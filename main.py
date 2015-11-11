# Copyright 2015 dc-tcs
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
#    Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.


import subprocess
import os
import json
import time
from decimal import Decimal

CURRENCY_NBT = 0
CURRENCY_NSR = 1
CURRENCY_BTC = 2

test_address ="BT9AWq9r1i6kghZc6LtrvNb2wRFh7JLCdP"

reference_gits =  {"dc-tcs" : "https://github.com/dc-tcs/flot-operations.git",
        "test" : "https://github.com/dc-tcs/flot-operations-test.git"}

my_id = "dc-tcs"
my_git = os.path.join(".","flot-operations")

def call_rpc(args):
    nud_path = 'nud'
    call_args = [nud_path] + args

    return call_args
    #return subprocess.check_output(call_args)


class BlockchainStream:
    def __init__(self, start_height, monitor):
        self.height = start_height
        self.current_block = subprocess.check_output([NUD_PATH,"getblockhash", start_height])
        self.monitor = monitor

    def advance(self):
        if self.current_block:
            s_json = json.loads(call_rpc(["getblock", self.current_block]))

            self.current_block = s_json[u'nextblockhash']
            return self.monitor(s_json)
        else:
            return None

class AddressInfo:
    def __init__(self, addr, unit, root = my_git):
        self.address = addr
        self.unspent = set()
        self.unit = unit
        self.last_block = 0
        self.signed_tx = ""
        self.signed_ids = []

        unspent = []

        addr_path = os.path.join(root, addr)

        if os.path.isdir(addr_path):
            addr_unspent_path = os.path.join(addr_path,'unspent')
            addr_tx_path = os.path.join(addr_path,'tx')

            if os.path.isfile(addr_unspent_path):
                with open(addr_unspent_path,"r") as f:
                    l = 0
                    cur_tx = ""
                    amount = Decimal(0)
                    for line in f:
                        if l == 0:
                            self.last_block = int(line)
                        elif l % 3 == 1:
                            cur_tx = line.strip()
                        elif l % 3 == 2:
                            amount = Decimal(line)
                        else:
                            unspent.add((cur_tx,amount,int(line.strip())))
                        l += 1

        else:
            if not os.path.exists(addr_path):
                os.makedirs(addr_path)
                #TODO: initialize unspent and tx files
    def get_unspent(self):
        return self.unspent

    def unspent_monitor(self, s_json):
        for txid in s_json[u'tx']:
            flag_changes = 0
            unspent_minus = set()
            unspent_plus = set()
            try:
                with open(os.devnull, "w") as fnull:
                    t_out = subprocess.check_output([NUD_PATH,"getrawtransaction", txid, "1"])

                t_json = json.loads(t_out)

                if t_out[u'unit'] == u'B':
                    for vi_json in t_json.get(u'vin'):
                        #Remove used inputs
                        vin_tx = vi_json.get(u'txid')
                        vin_tx_json = call_rpc(["getrawtransaction", vin_tx, "1"])
                        for vo_json in vin_tx_json.get(u'vout'):
                            if vo_json.get(u'addresses') = self.address:
                                amount = Decimal(vo_json.get(u'value'))
                                vout_n = int(vo_json.get(u'n'))
                                unspent_minus.add((vin_tx, amount, vout_n))

                    for vo_json in t_json.get(u'vout'):
                        #Add new outputs
                        if vo_json.get(u'addresses') == self.address:
                            amount = Decimal(vo_json.get(u'value'))
                            vout_n = int(vo_json.get(u'n'))
                            unspent_plus.add((txid, amount, vout_n))

            return unspent_minus, unspent_plus
            

    def update_outputs(self):
        flag_change = 0
        bstream = BlockchainStream(self.last_block + 1, self.unspent_monitor)
        while true:
            delta = BlockchainStream.advance()
            if delta:
                last_block += 1
                if len(delta[0]) + len(delta[1]) > 0:
                    #TODO: prompt difference
                    flag_change = 1
                    self.unspent.difference_update(delta[0])
                    self.unspent.update(delta[1])

                    print self.unspent
            else:
                break

        #TODO: push to own repo?
        return flag_change

    def get_spend_info(self, amount):
        unspent_list = sorted(unspent, key=lambda x: x[1])
        sum = Decimal(0)
        amount = Decimal(amount)
        i = 0
        while sum < amount and i < len(unspent_list):
            sum += unspent_list[i][1]
            i += 1
        if sum >= amount:
            #returns (change, list of inputs to spend)
            return (sum - amount, unspent_list[0:i])
        else:
            return None


def create_raw_transaction(amount, my_addr, recipient):
    #Note that amount should be a string
    spend_info = my_addr.get_spend_info(amount)

    st = "'["
    if spend_info:
        s = spend_info[1][0]
        
        st = st + "{\"txid\": \"" + s[0] + "\", \"vout\": " + "1" + "}"
        for s in spend_info[1][1:]:
            st = st + ",{\"txid\": \"" + s[0] + "\", \"vout\": " + "1" + "}" #TODO:change "1" to sth else
        st = st + "]'"

        sr = "'{\"" + recipient +"\": " + str(amount) + ", \"" + my_addr.address + "\": " + str(spend_info[0]) + "}'"

        return call_rpc(["create_raw_transaction",st,sr])
    else:
        return None

def sign_raw_transaction(raw_tx):
    return call_rpc(["signrawtransaction", raw_tx])

def git_update(git_folder):
    subprocess.call(['git', '-C', git_folder, 'add', '-A'])
    subprocess.call(['git', '-C', git_folder, 'commit', '-m', str(time.time())])
    subprocess.call(['git', '-C', git_folder, 'push', 'origin', 'master'])

def sign_and_push(raw_tx, my_addr, list_signed):
    s = sign_raw_transaction(raw_tx)
    if s:
        git_folder = os.path.join('.', my_git)
        tx_path = os.path.join('.', my_git, my_addr,'tx')

        with open(tx_path,'w') as f:
            f.writeline(s)
            for p in list_signed:
                f.writeline(p)
            f.writeline(my_id)
        git_update(git_folder)

root_ref = os.path.join(".","notmine")

def fetch_data(address_info):
    newest_unspent = address_info.unspent
    newest_rawtx = ""
    newest_signed_ids = []

    current_last_block = address_info.last_block

    for key, value in reference_gits.iteritems():
        git_folder = os.path.join(root_ref,key)

        if not os.path.exists(git_folder):
            subprocess.call(['git', 'clone', value, git_folder])

        try:
            s = subprocess.check_output(['git', '-C', git_folder, 'fetch', '--dry-run'])
            if s != "":
                subprocess.call(['git', '-C', git_folder, 'fetch'])

            a = AddressInfo(address_info.address, CURRENCY_NBT, root = git_folder)

            if a.last_block > current_last_block:
                yes = set(['yes','y', 'ye', ''])
                no = set(['no','n'])

                choice = raw_input("Newer snapshot found for unspent from: " + key + " - accept (Y/n)? ").lower()
                if choice in yes:
                    newest_unspent = a.unspent
                    current_last_block = a.last_block
        except:
            print "Error!"

    print ""
    return newest_unspent
                    #TODO: return latest transaction?

a = AddressInfo(test_address, CURRENCY_NBT)
a.unspent = fetch_data(a)

print create_raw_transaction("11.1", a, "testqqqqq")
