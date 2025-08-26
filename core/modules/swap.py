import time, random
from web3 import Web3
from eth_account import Account
from core.functions.web import get_real_nonce
from core.api.plume_api import PlumeApi
from core.plume import Plume
import settings, os, json


class PlumeSwap(Plume):
    def __init__(self):
        super().__init__()
        self.RelayRouter = settings.CONTRACT_ADDRESSES['RelayRouter']
        self.PLUME = settings.TOKENS['PLUME']
        self.pusd = settings.TOKENS['pusd']

        # Правильный путь к ABI
        self.ABI_PATH = os.path.join(
            os.path.dirname(__file__), "../abi/ValidatorFacet.json"
        )
        with open(self.ABI_PATH, "r") as f:
            self.contract_abi = json.load(f)


    @staticmethod
    def pad64(data: str) -> str:
        return data.rjust(64, "0")


    def get_estimate_gas(self, name, wallet, calldata, value):
        try:
            tx = {
                "from": wallet,
                "to": self.RelayRouter,
                "value": Web3.to_wei(value, "ether"),
                "data": calldata
            }
            return self.web3.eth.estimate_gas(tx)
        except Exception as e:
            self.log(name, f"❌ Ошибка estimate_gas: {e}")
            return

    
    # def build_complex_tx(self, wallet_from, account, name) -> dict:
    #     nonce = get_real_nonce(account.address, self.RPC_URL)
    #
    #     # ---- 1️⃣ Основные параметры ----
    #     method_id = "30be5567"
    #
    #     # value = round(random.uniform(0.02, 0.2), 2)
    #     value = 0.02
    #     value_wei = Web3.to_wei(value, 'ether')
    #     value_hex = hex(value_wei)
    #
    #     # ---- 2️⃣ Примеры аргументов ----
    #     print(hex(6)[2:])
    #     arg1 = self.pad64(hex(6)[2:])
    #     arg2 = self.pad64(hex(4)[2:])
    #     offset1 = self.pad64(hex(128)[2:])  # пример offset
    #     offset2 = self.pad64(hex(20)[2:])
    #     arg3 = self.pad64(hex(36)[2:])
    #     arg4 = self.pad64(hex(58)[2:])
    #
    #     address1 = self.pad64("ea237441c92cae6fc17caaf9a7acb3f953be4bd1")
    #     zeros = self.pad64("0")
    #     big_value = self.pad64(hex(value_wei)[2:])
    #
    #     # ---- 3️⃣ Пример массива / подписи ----
    #     hex_signature = "0d0e30db03f2e24c6531d8ae2f6c09d8e7a6ad7f7e87a81cb75dfda61c9d8328"
    #     hex_signature_padded = self.pad64(hex_signature)
    #
    #     # ---- 4️⃣ Вложенный вызов ----
    #     nested_method = "095ea7b3"
    #     spender = self.pad64("35e44dc4702fd51744001e248b49cbf9fcc51f0c")
    #     nested_value = big_value
    #
    #     nested_calldata = (
    #             nested_method +
    #             spender +
    #             nested_value +
    #             self.pad64("0") +
    #             self.pad64("0") +
    #             spender +
    #             self.pad64("0") * 4  # имитация структуры
    #     )
    #
    #     # ---- 5️⃣ Собираем calldata ----
    #     calldata = (
    #             "0x" + method_id +
    #             arg1 + arg2 + offset1 + offset2 + arg3 + arg4 +
    #             address1 + zeros + big_value + self.pad64("80") +
    #             hex_signature_padded + address1 + zeros * 2 +
    #             self.pad64("80") + self.pad64("44") + nested_calldata[:64] +
    #             nested_calldata[64:]  # если нужно склеить больше
    #     )
    #
    #     # ---- 6️⃣ Газ и Fees ----
    #     gas = hex(560000)
    #     max_fee_per_gas = hex(Web3.to_wei(5, "gwei"))
    #     priority_fee = hex(Web3.to_wei(2, "gwei"))
    #
    #     estimate_gas = self.get_estimate_gas(name, wallet_from, calldata, value_hex)
    #
    #     tx = {
    #         "chainId": 98866,
    #         "from": wallet_from,
    #         "to": self.RelayRouter,
    #         "value": value_hex,
    #         "data": calldata,
    #         "gas": gas,
    #         "maxFeePerGas": max_fee_per_gas,
    #         "maxPriorityFeePerGas": priority_fee,
    #         "nonce": hex(nonce)
    #     }
    #
    #     return tx

    # def build_complex_tx(self, wallet_from, account, name):
    #     nonce = get_real_nonce(account.address, self.RPC_URL)
    #     method_id = "30be5567"
    #
    #     value = 0.02
    #     value_wei = Web3.to_wei(value, 'ether')
    #     value_hex = hex(value_wei)
    #     big_value = self.pad64(hex(value_wei)[2:])
    #
    #     arg1 = self.pad64(hex(6)[2:])
    #     arg2 = self.pad64(hex(4)[2:])
    #     arg3 = self.pad64(hex(36)[2:])
    #     arg4 = self.pad64(hex(58)[2:])
    #     address1 = self.pad64("ea237441c92cae6fc17caaf9a7acb3f953be4bd1")
    #     zeros = self.pad64("0")
    #
    #     # ------- Signature block -------
    #     hex_signature = "0d0e30db03f2e24c6531d8ae2f6c09d8e7a6ad7f7e87a81cb75dfda61c9d8328"
    #     signature_block = (
    #             self.pad64(hex_signature) +
    #             address1 +
    #             zeros + zeros
    #     )
    #
    #     # ------- Nested calldata -------
    #     nested_method = "095ea7b3"
    #     spender = self.pad64("35e44dc4702fd51744001e248b49cbf9fcc51f0c")
    #     nested_value = big_value
    #
    #     nested_calldata = (
    #             nested_method +
    #             spender +
    #             nested_value +
    #             self.pad64("0") +
    #             self.pad64("0") +
    #             spender +
    #             self.pad64("0") * 4
    #     )
    #
    #     # ------- Calculate Offsets -------
    #     # STATIC = 10 слов = 320 байт
    #     static_size = 32 * 10
    #
    #     offset_sig = self.pad64(hex(static_size)[2:])
    #     offset_nested = self.pad64(hex(static_size + len(signature_block) // 2)[2:])
    #
    #     # ------- Build calldata -------
    #     calldata = (
    #             "0x" + method_id +
    #             arg1 + arg2 + offset_sig + offset_nested +
    #             arg3 + arg4 +
    #             address1 + zeros + big_value +
    #             offset_sig +
    #             signature_block +
    #             nested_calldata
    #     )
    #
    #     print(f"len(calldata) = {len(calldata)}")
    #     print(calldata)
    #
    #     gas = self.get_estimate_gas(name, wallet_from, calldata, value_hex)
    #     tx = {
    #         "chainId": 98866,
    #         "from": wallet_from,
    #         "to": self.RelayRouter,
    #         "value": value_hex,
    #         "data": calldata,
    #         "gas": gas,
    #         "maxFeePerGas": hex(Web3.to_wei(5, "gwei")),
    #         "maxPriorityFeePerGas": hex(Web3.to_wei(2, "gwei")),
    #         "nonce": hex(nonce)
    #     }
    #
    #     return tx

    def get_pair_exists(router, token_a, token_b):
        # Проверяет, существует ли пара token_a и token_b в пуле через метод getPairState
        try:
            reserveA, reserveB, fee, pair = router.functions.getPairState(token_a, token_b).call()
            return pair != "0x0000000000000000000000000000000000000000"
        except Exception as e:
            print(f"❌ Ошибка при проверке пары: {e}")
            return False


    def build_complex_tx(self, wallet, account, name):
        router_address = self.web3.to_checksum_address(self.RelayRouter)

        token_in = self.web3.to_checksum_address(self.PLUME)
        token_out = self.web3.to_checksum_address(self.pusd)
        wallet = self.web3.to_checksum_address(wallet)

        router = self.web3.eth.contract(address=router_address, abi=self.contract_abi)

        if not self.get_pair_exists(router, token_in, token_out):
            print("❌ Пара токенов не найдена в пуле, операция отменена.")
            return

        print(router_address)

        tx = 1
        return tx

    def run_single(self, name, wallet, pk):
        account = Account.from_key(pk)
        tx = self.build_complex_tx(wallet, account, name)
        print(tx)


    # # Пример вызова:
    # if __name__ == "__main__":
    #     tx = build_transaction(
    #         wallet_address="0x0F03a02e57455473C655F59b2cd207914Db7a122",
    #         to_contract="0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222",
    #         value_eth=0.5,
    #         validator_id=2,
    #         nonce=42
    #     )
    #     print(json.dumps(tx, indent=2))
