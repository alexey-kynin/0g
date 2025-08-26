import aiohttp
import asyncio

from datetime import datetime, timezone
from eth_account import Account
from web3 import AsyncWeb3, Web3
from eth_account.messages import encode_defunct


class Login:
    def __init__(self, web3: AsyncWeb3, account: Account, pharos_ref: str = ""):
        self.web3 = web3
        self.account = account
        self.pharos_ref = pharos_ref  # Доп. параметр из примера
        self._nonce_lock = asyncio.Lock()
        self._nonce = None

    async def login(self):
        dt = datetime.now(timezone.utc)
        issued_at = dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        domain = "testnet.pharosnetwork.xyz"
        uri = "https://testnet.pharosnetwork.xyz"
        chain_id = 688688

        # Получаем nonce
        async with self._nonce_lock:
            if self._nonce is None:
                self._nonce = await self.web3.eth.get_transaction_count(self.account.address)
            else:
                self._nonce += 1
            nonce = self._nonce

        address = self.web3.to_checksum_address(self.account.address)

        message = (
            f"{domain} wants you to sign in with your Ethereum account:\n"
            f"{address}\n\n"
            f"I accept the Pharos Terms of Service: {domain}/privacy-policy/Pharos-PrivacyPolicy.pdf\n\n"
            f"URI: {uri}\n\n"
            f"Version: 1\n\n"
            f"Chain ID: {chain_id}\n\n"
            f"Nonce: {nonce}\n\n"
            f"Issued At: {issued_at}"
        )

        encoded_message = encode_defunct(text=message)
        signed_message = self.account.sign_message(encoded_message)

        signature = signed_message.signature.hex()
        if not signature.startswith("0x"):
            signature = "0x" + signature

        payload = {
            "address": address,
            "chain_id": str(chain_id),
            "domain": domain,
            "invite_code": self.pharos_ref,
            "nonce": str(nonce),
            "signature": signature,
            "timestamp": issued_at,
            "wallet": "Rabby Wallet"
        }

        headers = {
            "Content-Type": "application/json",
            "Referer": "https://testnet.pharosnetwork.xyz"
        }

        url = "https://api.pharosnetwork.xyz/user/login"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                status = response.status
                text = await response.text()
                print(f"\nStatus Code: {status}")
                print(f"Response: {text}")

                if status == 200:
                    data = await response.json()
                    jwt = data.get("data", {}).get("jwt")
                    print(f"\nYour JWT: {jwt}")
                    return jwt
                else:
                    return None