import requests
import certifi


class PlumeApi:
    BASE_URL = "https://explorer-plume-mainnet-1.t.conduit.xyz/api/v2/addresses/"

    def __init__(self, address: str):
        self.address = address

    def get_native_balance(self) -> int:
        url = f"{self.BASE_URL}{self.address}"
        try:
            # response = requests.get(url, timeout=10, verify=certifi.where())
            # response = requests.get(url, timeout=10, verify="cacert.pem")
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            balance = int(data.get("coin_balance", 0))

            print(f"🔎 Адрес: {self.address} | Баланс: {balance/10**18}")
            return balance
        except requests.RequestException as e:
            print(f"❌ Ошибка запроса: {e}")
            return 0


    def get_gas(self) -> int:
        url = f"https://explorer-plume-mainnet-1.t.conduit.xyz/api/v2/stats"
        try:
            # response = requests.get(url, timeout=10, verify=certifi.where())
            # response = requests.get(url, timeout=10, verify="cacert.pem")
            response = requests.get(url, timeout=10, verify=False)
            # response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            gas_prices = data.get("gas_prices", 0)
            print(gas_prices)
            print(f"🔎 Normal Gas: {gas_prices['average']}")
            return 1
        except requests.RequestException as e:
            print(f"❌ Ошибка запроса: {e}")
            return 0

# ------------------------------
# if __name__ == "__main__":
#     # Пример вызова
#     addr = "0x3Df6837d297688C07575F9C0949B8A76c8C8f671"
#     explorer = PlumeBalance(addr)
#     balance = explorer.get_native_balance()
#     print(f"Нативный баланс: {balance}")
