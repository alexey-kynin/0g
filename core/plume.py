import json, os
import time, random
from web3 import Web3
import settings
from core.database.db import WalletDatabase


class Plume:
    def __init__(self):
        self.MAX_RETRIES = 3

        # Правильный путь к ABI
        self.ABI_PATH = os.path.join(
            os.path.dirname(__file__), "../abi/plume_contract_abi.json"
        )
        with open(self.ABI_PATH, "r") as f:
            self.contract_abi = json.load(f)

        self.RPC_URL = settings.RPCS['plume']

        self.db = WalletDatabase()
        self.private_keys = self.db.get_active_private_keys()
        self.web3 = Web3(Web3.HTTPProvider(self.RPC_URL))

    def log(self, name, msg):
        print(f"[Wal:{name}] {msg}")

    def run_for_all(self):
        for name, wallet, pk in self.private_keys:
            self.run_single(name, wallet, pk)
            print('----' * 40)
            time.sleep(random.uniform(1, 2))

