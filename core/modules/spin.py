import time, random
from web3 import Web3
from eth_account import Account
from core.functions.web import get_real_nonce
from core.plume import Plume
import settings


class PlumeSpinner(Plume):
    def __init__(self):
        super().__init__()
        self.TO_ADDRESS = settings.CONTRACT_ADDRESSES['spin']

    def run_single(self, name, wallet, pk):
        account = Account.from_key(pk)

        contract = self.web3.eth.contract(address=self.TO_ADDRESS, abi=self.contract_abi)

        # data: вызов функции через контракт, а не raw
        try:
            estimate_gas = contract.functions.startSpin().estimate_gas({
                "from": account.address,
                "value": Web3.to_wei(2, "ether")
            })
        except Exception as e:
            self.log(name, f"❌ Ошибка estimate_gas: {e}")
            return

        nonce = get_real_nonce(account.address, self.RPC_URL)
        gas_price = self.web3.eth.gas_price

        tx = {
            "chainId": self.web3.eth.chain_id,
            "nonce": nonce,
            "to": Web3.to_checksum_address(self.TO_ADDRESS),
            "value": Web3.to_wei(2, "ether"),
            "gas": int(estimate_gas * 1.2),
            "gasPrice": gas_price,
            "data": "0xac6bc853",
            # "data": contract.encodeABI(fn_name="startSpin")
        }
        self.log(name, tx)

        signed_tx = account.sign_transaction(tx)
        tx_hash = signed_tx.hash

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.log(name, f"🚀 Попытка отправки {attempt}: {tx_hash.hex()}")
                self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
                self.log(name, f"✅ Успешно: {tx_hash.hex()}")
                self.log(name, f"📦 Квитанция: {receipt}")
                break
            except Exception as e:
                error_text = str(e)
                if "nonce too low" in error_text or "already known" in error_text:
                    self.log(name, "⚠️ Уже в сети — проверим...")
                    try:
                        receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                        if receipt:
                            self.log(name, f"📦 Уже обработана: {receipt}")
                            break
                    except:
                        self.log(name, "❌ Не получили квитанцию")
                        time.sleep(3)
                        continue

                self.log(name, f"❌ Ошибка отправки: {e}")
                if attempt == self.MAX_RETRIES:
                    self.log(name, "🛑 Стоп после трёх попыток")
                else:
                    time.sleep(3)

        time.sleep(random.uniform(1, 2))
