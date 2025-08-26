import asyncio
import random
import requests
import aiohttp
from loguru import logger
from eth_account import Account
import primp
from web3 import AsyncWeb3
from datetime import datetime, timezone

# from src.model.pharos_xyz.bean import BeanDex
# from src.model.pharos_xyz.ambient import AmbientDex
from src.model.pharos_xyz.izumi import IzumiDex
from src.model.pharos_xyz.raffle import Raffle
# from src.model.pharos_xyz.uniswap_swaps import MonadSwap
# from src.model.pharos_xyz.faucet import faucet

from src.utils.config import Config
from src.utils.constants import RPCS_PHAROS
from src.model.pharos_xyz.constants import PHAROS_REF

from eth_account.messages import encode_defunct


class PharosXYZ:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        account_data,
        # discord_token: str,
        config: Config,
        session: primp.AsyncClient,
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = account_data[2]
        self.name = account_data[0]
        # self.discord_token = discord_token
        self.config = config
        self.session: primp.AsyncClient = session

        self._nonce_lock = asyncio.Lock()
        self._nonce = None

        self.account = Account.from_key(account_data[2])

        self.web3 = AsyncWeb3(
             AsyncWeb3.AsyncHTTPProvider(
                 RPCS_PHAROS,
                 request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
             )
        )

        self.wallet_address = self.web3.to_checksum_address(self.account.address)
        self.pharos_ref = account_data[3]


    async def swaps(self, type: str):
        try:
            # if type == "swaps":
            #     number_of_swaps = random.randint(
            #         self.config.FLOW.NUMBER_OF_SWAPS[0], self.config.FLOW.NUMBER_OF_SWAPS[1]
            #     )
            #     logger.info(f"[{self.account_index}] | Will perform {number_of_swaps} swaps")
            #
            #     for swap_num in range(number_of_swaps):
            #         success = False
            #         for retry in range(self.config.SETTINGS.ATTEMPTS):
            #             try:
            #                 swapper = MonadSwap(self.private_key, self.proxy)
            #                 amount = random.randint(
            #                     self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[0],
            #                     self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[1],
            #                 )
            #                 random_token = random.choice(["DAK", "YAKI", "CHOG"])
            #                 logger.info(
            #                     f"[{self.account_index}] | Swapping {amount}% of balance to {random_token}"
            #                 )
            #
            #                 await swapper.swap(
            #                     percentage_to_swap=amount, token_out=random_token,
            #                 )
            #                 random_pause = random.randint(
            #                     self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
            #                     self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
            #                 )
            #                 logger.success(
            #                     f"[{self.account_index}] | Swapped {amount}% of balance to {random_token}. Swap {swap_num + 1}/{number_of_swaps}. Next swap in {random_pause} seconds"
            #                 )
            #                 await asyncio.sleep(random_pause)
            #                 success = True
            #                 break  # Break retry loop on success
            #
            #             except Exception as e:
            #                 logger.error(
            #                     f"[{self.account_index}] | Error swap in monad.xyz ({retry + 1}/{self.config.SETTINGS.ATTEMPTS}): {e}"
            #                 )
            #                 if retry == self.config.SETTINGS.ATTEMPTS - 1:
            #                     raise  # Re-raise if all retries failed
            #                 continue
            #
            #         if not success:
            #             logger.error(f"[{self.account_index}] | Failed to complete swap {swap_num + 1}/{number_of_swaps} after all retries")
            #             break
            #
            #     return True
            #
            # elif type == "ambient":
            #     number_of_swaps = random.randint(
            #         self.config.FLOW.NUMBER_OF_SWAPS[0], self.config.FLOW.NUMBER_OF_SWAPS[1]
            #     )
            #     logger.info(f"[{self.account_index}] | Will perform {number_of_swaps} Ambient swaps")
            #
            #     for swap_num in range(number_of_swaps):
            #         success = False
            #         for retry in range(self.config.SETTINGS.ATTEMPTS):
            #             try:
            #                 swapper = AmbientDex(self.private_key, self.proxy, self.config)
            #                 amount = random.randint(
            #                     self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[0],
            #                     self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[1],
            #                 )
            #                 await swapper.swap(
            #                     percentage_to_swap=amount,
            #                     type="swap",
            #                 )
            #                 random_pause = random.randint(
            #                     self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
            #                     self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
            #                 )
            #                 logger.success(
            #                     f"[{self.account_index}] | Completed Ambient swap {swap_num + 1}/{number_of_swaps}. Next swap in {random_pause} seconds"
            #                 )
            #                 await asyncio.sleep(random_pause)
            #                 success = True
            #                 break  # Break retry loop on success
            #
            #             except Exception as e:
            #                 logger.error(
            #                     f"[{self.account_index}] | Error swap in ambient ({retry + 1}/{self.config.SETTINGS.ATTEMPTS}): {e}"
            #                 )
            #                 if retry == self.config.SETTINGS.ATTEMPTS - 1:
            #                     raise  # Re-raise if all retries failed
            #                 continue
            #
            #         if not success:
            #             logger.error(f"[{self.account_index}] | Failed to complete swap {swap_num + 1}/{number_of_swaps} after all retries")
            #             break
            #
            #     return True
            #
            # elif type == "bean":
            #     number_of_swaps = random.randint(
            #         self.config.FLOW.NUMBER_OF_SWAPS[0], self.config.FLOW.NUMBER_OF_SWAPS[1]
            #     )
            #     logger.info(f"[{self.account_index}] | Will perform {number_of_swaps} Bean swaps")
            #
            #     for swap_num in range(number_of_swaps):
            #         success = False
            #         for retry in range(self.config.SETTINGS.ATTEMPTS):
            #             try:
            #                 swapper = BeanDex(self.private_key, self.proxy, self.config)
            #                 amount = random.randint(
            #                     self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[0],
            #                     self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[1],
            #                 )
            #                 await swapper.swap(
            #                     percentage_to_swap=amount,
            #                     type="swap",
            #                 )
            #                 random_pause = random.randint(
            #                     self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
            #                     self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
            #                 )
            #                 logger.success(
            #                     f"[{self.account_index}] | Completed Bean swap {swap_num + 1}/{number_of_swaps}. Next swap in {random_pause} seconds"
            #                 )
            #                 await asyncio.sleep(random_pause)
            #                 success = True
            #                 break  # Break retry loop on success
            #
            #             except Exception as e:
            #                 logger.error(
            #                     f"[{self.account_index}] | Error swap in bean ({retry + 1}/{self.config.SETTINGS.ATTEMPTS}): {e}"
            #                 )
            #                 if retry == self.config.SETTINGS.ATTEMPTS - 1:
            #                     raise  # Re-raise if all retries failed
            #                 continue
            #
            #         if not success:
            #             logger.error(f"[{self.account_index}] | Failed to complete swap {swap_num + 1}/{number_of_swaps} after all retries")
            #             break
            #
            #     return True
            #
            # elif type == "izumi":
            if type == "izumi":
                number_of_swaps = random.randint(
                    self.config.FLOW.NUMBER_OF_SWAPS[0], self.config.FLOW.NUMBER_OF_SWAPS[1]
                )
                logger.info(f"[{self.name}:{self.account_index}] | Will perform {number_of_swaps} Izumi swaps")
                for swap_num in range(number_of_swaps):
                    success = False
                    for retry in range(self.config.SETTINGS.ATTEMPTS):
                        try:
                            swapper = IzumiDex(self.private_key, self.proxy, self.config)
                            amount = random.uniform(
                                self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[0],
                                self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP[1],
                            )

                            await swapper.swap(
                                percentage_to_swap=amount,
                                type="swap",
                            )

                            random_pause = random.randint(
                                self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
                                self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
                            )
                            logger.success(
                                f"[{self.account_index}] | Completed Izumi swap {swap_num + 1}/{number_of_swaps}. Next swap in {random_pause} seconds"
                            )
                            await asyncio.sleep(random_pause)
                            success = True
                            break  # Break retry loop on success
                            
                        except Exception as e:
                            logger.error(
                                f"[{self.account_index}] | Error swap in izumi ({retry + 1}/{self.config.SETTINGS.ATTEMPTS}): {e}"
                            )
                            if retry == self.config.SETTINGS.ATTEMPTS - 1:
                                raise  # Re-raise if all retries failed
                            continue
                    
                    if not success:
                        logger.error(f"[{self.account_index}] | Failed to complete swap {swap_num + 1}/{number_of_swaps} after all retries")
                        break

                return True
            

                return success  # Return True if succeeded, False if all retries failed
        except Exception as e:
            logger.error(f"[{self.account_index}] | Error swaps: {e}")
            return False


    async def raffle(self):
        number_of_swaps = random.randint(
            self.config.FLOW.NUMBER_OF_SWAPS[0], self.config.FLOW.NUMBER_OF_SWAPS[1]
        )
        logger.info(f"[{self.name}:{self.account_index}] | Will perform {number_of_swaps} Raffle Tickets")
        for swap_num in range(number_of_swaps):
            success = False
            for retry in range(self.config.SETTINGS.ATTEMPTS):
                try:
                    raffle = Raffle(self.private_key, self.proxy, self.config)

                    await raffle.add_tickets()

                    random_pause = random.randint(
                        self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
                        self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
                    )
                    logger.success(
                        f"[{self.account_index}] | Completed Raffle Tickets {swap_num + 1}/{number_of_swaps}. Next Raffle Tickets in {random_pause} seconds"
                    )
                    await asyncio.sleep(random_pause)
                    success = True
                    break  # Break retry loop on success

                except Exception as e:
                    logger.error(
                        f"[{self.account_index}] | Error Raffle Tickets ({retry + 1}/{self.config.SETTINGS.ATTEMPTS}): {e}"
                    )
                    if retry == self.config.SETTINGS.ATTEMPTS - 1:
                        raise  # Re-raise if all retries failed
                    continue

            if not success:
                logger.error(
                    f"[{self.account_index}] | Failed to complete swap {swap_num + 1}/{number_of_swaps} after all retries")
                break

        return True


    async def sign_in(self, jwt: str):
        url = "https://api.pharosnetwork.xyz/sign/in"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {jwt}",
            "Origin": "https://testnet.pharosnetwork.xyz",
            "Referer": "https://testnet.pharosnetwork.xyz/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        }

        payload = {
            "address": self.wallet_address,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                status = response.status
                text = await response.text()

                print(f"\nStatus Code: {status}")
                print(f"Response: {text}")

                return status, text

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
                    await self.sign_in(jwt)
                else:
                    return None

    async def chekin(self):
        print(self.proxy)
        await self.login()


    # async def connect_discord(self):
    #     for retry in range(self.config.SETTINGS.ATTEMPTS):
    #         try:
    #             headers = {
    #                 "sec-ch-ua-platform": '"Windows"',
    #                 "content-type": "application/json",
    #                 "sec-ch-ua-mobile": "?0",
    #                 "accept": "*/*",
    #                 "sec-fetch-site": "same-origin",
    #                 "sec-fetch-mode": "cors",
    #                 "sec-fetch-dest": "empty",
    #                 "referer": "https://testnet.monad.xyz/",
    #                 "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5",
    #                 "priority": "u=1, i",
    #             }
    #
    #             response = await self.session.get(
    #                 "https://testnet.monad.xyz/api/auth/csrf", headers=headers
    #             )
    #
    #             if response.status_code == 200:
    #                 csrf_token = response.json().get("csrfToken")
    #                 headers = {
    #                     "sec-ch-ua-platform": '"Windows"',
    #                     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    #                     "content-type": "application/x-www-form-urlencoded",
    #                     "sec-ch-ua-mobile": "?0",
    #                     "accept": "*/*",
    #                     "origin": "https://testnet.monad.xyz",
    #                     "sec-fetch-site": "same-origin",
    #                     "sec-fetch-mode": "cors",
    #                     "sec-fetch-dest": "empty",
    #                     "referer": "https://testnet.monad.xyz/",
    #                     "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5",
    #                     "priority": "u=1, i",
    #                 }
    #
    #                 data = {
    #                     "csrfToken": csrf_token,
    #                     "callbackUrl": "https://testnet.monad.xyz/",
    #                     "json": "true",
    #                 }
    #
    #                 response = await self.session.post(
    #                     "https://testnet.monad.xyz/api/auth/signin/discord",
    #                     headers=headers,
    #                     data=data,
    #                 )
    #                 if response.status_code == 200:
    #                     url = response.json().get("url")
    #                     state = url.split("state=")[1].strip()
    #
    #                     headers = {
    #                         "sec-ch-ua-platform": '"Windows"',
    #                         "authorization": self.discord_token,
    #                         "x-debug-options": "bugReporterEnabled",
    #                         "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="131", "Chromium";v="131"',
    #                         "sec-ch-ua-mobile": "?0",
    #                         "x-discord-timezone": "Etc/GMT-2",
    #                         "x-discord-locale": "en-US",
    #                         "content-type": "application/json",
    #                         "accept": "*/*",
    #                         "origin": "https://discord.com",
    #                         "sec-fetch-site": "same-origin",
    #                         "sec-fetch-mode": "cors",
    #                         "sec-fetch-dest": "empty",
    #                         "referer": f"https://discord.com/oauth2/authorize?client_id=1330973073914069084&scope=identify%20email%20guilds%20guilds.members.read&response_type=code&redirect_uri=https%3A%2F%2Ftestnet.monad.xyz%2Fapi%2Fauth%2Fcallback%2Fdiscord&state={state}",
    #                         "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5",
    #                         "priority": "u=1, i",
    #                     }
    #
    #                     params = {
    #                         "client_id": "1330973073914069084",
    #                         "response_type": "code",
    #                         "redirect_uri": "https://testnet.monad.xyz/api/auth/callback/discord",
    #                         "scope": "identify email guilds guilds.members.read",
    #                         "state": state,
    #                     }
    #
    #                     json_data = {
    #                         "permissions": "0",
    #                         "authorize": True,
    #                         "integration_type": 0,
    #                         "location_context": {
    #                             "guild_id": "10000",
    #                             "channel_id": "10000",
    #                             "channel_type": 10000,
    #                         },
    #                     }
    #
    #                     response = await self.session.post(
    #                         "https://discord.com/api/v9/oauth2/authorize",
    #                         params=params,
    #                         headers=headers,
    #                         json=json_data,
    #                     )
    #
    #                     if response.status_code == 200:
    #                         location = response.json().get("location")
    #                         code = location.split("code=")[1].split("&")[0]
    #                         headers = {
    #                             "sec-ch-ua-mobile": "?0",
    #                             "sec-ch-ua-platform": '"Windows"',
    #                             "upgrade-insecure-requests": "1",
    #                             "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    #                             "sec-fetch-site": "cross-site",
    #                             "sec-fetch-mode": "navigate",
    #                             "sec-fetch-user": "?1",
    #                             "sec-fetch-dest": "document",
    #                             "referer": "https://discord.com/",
    #                             "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6,zh;q=0.5",
    #                             "priority": "u=0, i",
    #                         }
    #
    #                         params = {
    #                             "code": code,
    #                             "state": state,
    #                         }
    #
    #                         response = await self.session.get(
    #                             "https://testnet.monad.xyz/api/auth/callback/discord",
    #                             params=params,
    #                             headers=headers,
    #                         )
    #                         if response.status_code == 200:
    #                             logger.success(
    #                                 f"[{self.account_index}] | Discord connected!"
    #                             )
    #                             return True
    #                         else:
    #                             logger.error(
    #                                 f"[{self.account_index}] | Failed to connect to discord: {response.text}"
    #                             )
    #                             continue
    #                     else:
    #                         logger.error(
    #                             f"[{self.account_index}] | Failed to connect to discord: {response.text}"
    #                         )
    #                         continue
    #
    #             else:
    #                 logger.error(
    #                     f"[{self.account_index}] | Failed to get csrf token: {response.text}"
    #                 )
    #                 continue
    #
    #         except Exception as e:
    #             random_pause = random.randint(
    #                 self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
    #                 self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
    #             )
    #             logger.error(
    #                 f"[{self.account_index}] | Error connect discord to monad.xyz ({retry + 1}/{self.config.SETTINGS.ATTEMPTS}): {e}. Next connect in {random_pause} seconds"
    #             )
    #             await asyncio.sleep(random_pause)
    #             continue
    #     return False
