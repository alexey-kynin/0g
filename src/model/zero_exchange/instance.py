import asyncio
import random
import time, json
import base64
import aiohttp

import primp
from asyncio import sleep
from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3, Web3
from web3.exceptions import TransactionNotFound
from web3.contract import AsyncContract

from typing import Dict, Optional, List, Tuple, Any, Union
from pathlib import Path
from src.utils.config import Config
from src.utils.decorators import retry

from web3.types import TxParams
from eth_typing import HexStr

from src.model.onchain.utils import Utils

from .constants import *


class ZeroExchange:
    def __init__(
            self,
            account_index: int,
            proxy: str,
            account_data: str,
            config: Config,
            session: primp.AsyncClient,
            # session: Optional[AsyncClient] = None,
    ):
        self.private_key = account_data[2]
        self.proxy = proxy
        self.session = session
        self.name = account_data[0]

        self.web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(
                RPC_GALILEO,
                request_kwargs={"proxy": f"http://{proxy}", "ssl": False} if proxy else {}
            )
        )
        self.account = Account.from_key(self.private_key)
        self.wallet_address = self.web3.to_checksum_address(self.account.address)
        self.utils = Utils
        self.pharos_ref = account_data[3]
        self._nonce_lock = asyncio.Lock()
        self._nonce = None

        # self.ABI_PATH = Path(__file__).resolve().parent.parent.parent.parent / "abi" / "zenith_quoter.json"
        # with open(self.ABI_PATH , "r") as f:
        #     self.quoter_abi = json.load(f)
        #
        # self.ABI_PATH = Path(__file__).resolve().parent.parent.parent.parent / "abi" / "zenith.json"
        # with open(self.ABI_PATH , "r") as f:
        #     self.abi = json.load(f)
        #
        # self.ABI_PATH = Path(__file__).resolve().parent.parent.parent.parent / "abi" / "zenith_positions.json"
        # with open(self.ABI_PATH, "r") as f:
        #     self.zenith_positions = json.load(f)


    async def get_wallet_balance(self, is_native: bool, address: str = None) -> int:
        if not is_native:
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(address), abi=ERC20_ABI
            )
            balance = await contract.functions.balanceOf(self.wallet_address).call()
        else:
            balance = await self.web3.eth.get_balance(self.wallet_address)

        return balance


    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def execute_swap(self):
        print(1)
        native_balance = await self.utils.get_balance(self.wallet_address)
        print(native_balance)


    async def swap(self, to_token=None) -> Optional[str]:

        num_executions = 1
        # num_executions = random.randint(3, 7)
        logger.info(f"Будет выполнено Swap {num_executions} раз")

        for i in range(1, num_executions + 1):
            if i > 1:
                delay = random.uniform(16, 42)
                logger.info(f"Вызов #{i} - задержка {delay:.2f} сек")
                await asyncio.sleep(delay)
            await self.execute_swap()

        logger.success("Все вызовы Swap завершены")
