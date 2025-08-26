import time, random
from web3 import Web3
from eth_account import Account
from core.functions.web import get_real_nonce
from core.api.plume_api import PlumeApi
from core.plume import Plume
import settings


class PlumeStake(Plume):
    def __init__(self):
        super().__init__()
        self.TO_ADDRESS = settings.CONTRACT_ADDRESSES['stake']


    def get_calldata(self):
        method_id = "0x2f57ee41"
        validator_id = random.choice([1, 2, 4, 7, 9, 8, 10])
        arg_hex = hex(validator_id)[2:].rjust(64, "0")
        return method_id + arg_hex


    def run_single(self, name, wallet, pk):
        value = round(random.uniform(0.2, 1), 2)
        account = Account.from_key(pk)
        plume_api = PlumeApi(wallet)

        balance = plume_api.get_native_balance()
        if balance / 10**18 < 5:
            self.log(name, f"💧 Недостаточный баланс: {balance/10**18:.3f} PLUME")
            return

        self.log(name, f"✅ Баланс: {balance/10**18:.3f} PLUME")

        calldata = self.get_calldata()

        try:
            tx = {
                "from": wallet,
                "to": self.TO_ADDRESS,
                "value": Web3.to_wei(value, "ether"),
                "data": calldata
            }
            estimate_gas = self.web3.eth.estimate_gas(tx)
        except Exception as e:
            self.log(name, f"❌ Ошибка estimate_gas: {e}")
            return
        nonce = get_real_nonce(account.address, self.RPC_URL)

        gas_prices = plume_api.get_gas()
        if not gas_prices:
            gas_prices = 1000  # Gwei

        max_fee_per_gas = Web3.to_wei(gas_prices * 1.1, "gwei")
        priority_fee = Web3.to_wei(2, "gwei")

        base_fee = self.web3.eth.get_block('pending').baseFeePerGas
        self.log(name, f"Base fee: {base_fee}, Max fee: {max_fee_per_gas}")

        if max_fee_per_gas <= base_fee:
            max_fee_per_gas = int(base_fee * 1.1)

        tx = {
            "chainId": self.web3.eth.chain_id,
            "from": wallet,
            "to": self.TO_ADDRESS,
            "value": Web3.to_wei(value, "ether"),
            "data": calldata,
            "gas": int(estimate_gas * 1.02),
            "maxFeePerGas": int(max_fee_per_gas),
            "maxPriorityFeePerGas": int(priority_fee),
            "nonce": nonce
        }

        self.log(name, tx)

        signed_tx = account.sign_transaction(tx)
        tx_hash = signed_tx.hash

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.log(name, f"🚀 Попытка {attempt}: {tx_hash.hex()}")
                self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
                self.log(name, f"✅ Успешно: {tx_hash.hex()}")
                self.log(name, f"📦 Квитанция: {receipt}")
                break
            except Exception as e:
                self.log(name, f"❌ Ошибка: {e}")
                if attempt == self.MAX_RETRIES:
                    self.log(name, "🛑 Прекращаем")
                else:
                    time.sleep(3)
