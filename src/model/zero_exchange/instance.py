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
from web3 import Web3 as SyncWeb3
from eth_abi import abi

from typing import Dict, Optional, List, Tuple, Any, Union
from pathlib import Path
from src.utils.config import Config
from .utills import Utils
from .utills import retry

from src.utils.balance import Balance
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
                address=self.web3.to_checksum_address(address), abi=ERC_20_ABI
            )
            balance = await contract.functions.balanceOf(self.wallet_address).call()
        else:
            balance = await self.web3.eth.get_balance(self.wallet_address)

        return balance


    async def get_token_balance(
        self,
        wallet_address: str,
        token_address: str,
        token_abi: list = None,
        decimals: int = 18,
        symbol: str = "TOKEN",
    ) -> Balance:

        if token_abi is None:
            # Use minimal ERC20 ABI if none provided
            token_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                }
            ]

        token_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address), abi=token_abi
        )
        wei_balance = await token_contract.functions.balanceOf(wallet_address).call()

        return Balance.from_wei(wei_balance, decimals=decimals, symbol=symbol)


    async def get_gas_params(self) -> Dict[str, int]:
        try:
            # Try EIP-1559 first
            latest_block = await self.web3.eth.get_block("latest")

            # Check if the network supports EIP-1559
            if "baseFeePerGas" in latest_block:
                base_fee = latest_block["baseFeePerGas"]
                max_priority_fee = await self.web3.eth.max_priority_fee
                max_fee = base_fee + max_priority_fee

                return {
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority_fee,
                }
            else:
                # Fallback to legacy gas pricing
                gas_price = await self.web3.eth.gas_price
                return {"gasPrice": gas_price}

        except Exception as e:
            logger.error(
                f"Failed to get gas parameters: {str(e)}"
            )
            raise

    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def execute_transaction(
            self,
            tx_data: Dict,
            chain_id: int,
            explorer_url: Optional[str] = None,
    ) -> str:
        try:
            nonce = await self.web3.eth.get_transaction_count(self.wallet_address)
            gas_params = await self.get_gas_params()
            if gas_params is None:
                raise Exception("Failed to get gas parameters")

            transaction = {
                "from": self.wallet_address,
                "nonce": nonce,
                "chainId": chain_id,
                **tx_data,
                **gas_params,
            }

            # Add type 2 only for EIP-1559 transactions
            if "maxFeePerGas" in gas_params:
                transaction["type"] = 2

            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = await self.web3.eth.send_raw_transaction(
                signed_txn.raw_transaction
            )

            logger.info(
                f"Waiting for transaction confirmation..."
            )
            receipt = await self.web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=240, poll_latency=2
            )

            if receipt["status"] == 1:
                tx_hex = tx_hash.hex()
                success_msg = f"Transaction successful!"
                if explorer_url:
                    success_msg += f" Explorer URL: {explorer_url}{tx_hex}"
                logger.success(success_msg)
                return tx_hex
            else:
                raise Exception("Transaction failed")
        except Exception as e:
            error_msg = str(e)
            if "tx already in mempool" in error_msg:
                logger.info(f"Transaction already in mempool")
                return True
            logger.error(
                f"Transaction execution failed: {error_msg}"
            )
            raise


    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def approve_token(
        self,
        token_address: str,
        spender_address: str,
        amount: int,
        chain_id: int,
        token_abi: list = None,
        explorer_url: Optional[str] = None,
    ) -> Optional[str]:

        try:
            if token_abi is None:
                # Use minimal ERC20 ABI if none provided
                token_abi = [
                    {
                        "constant": True,
                        "inputs": [
                            {"name": "_owner", "type": "address"},
                            {"name": "_spender", "type": "address"},
                        ],
                        "name": "allowance",
                        "outputs": [{"name": "", "type": "uint256"}],
                        "type": "function",
                    },
                    {
                        "constant": False,
                        "inputs": [
                            {"name": "_spender", "type": "address"},
                            {"name": "_value", "type": "uint256"},
                        ],
                        "name": "approve",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function",
                    },
                ]

            token_contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(token_address), abi=token_abi
            )

            current_allowance = await token_contract.functions.allowance(
                self.wallet_address, spender_address
            ).call()

            if current_allowance >= amount:
                logger.info(
                    f" Allowance sufficient for token {token_address}"
                )
                return None

            gas_params = await self.get_gas_params()
            if gas_params is None:
                raise Exception("Failed to get gas parameters")

            approve_tx = await token_contract.functions.approve(
                spender_address, amount
            ).build_transaction(
                {
                    "from": self.wallet_address,
                    "nonce": await self.web3.eth.get_transaction_count(self.wallet_address),
                    "chainId": chain_id,
                    **gas_params,
                }
            )

            return await self.execute_transaction(
                approve_tx, chain_id=chain_id, explorer_url=explorer_url
            )

        except Exception as e:
            logger.error(
                f"Failed to approve token {token_address}: {str(e)}"
            )
            raise


    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def estimate_gas(self, transaction: dict) -> int:
        """Estimate gas for transaction and add some buffer."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            # Добавляем 10% к estimated gas для безопасности
            return int(estimated * 2.2)
        except Exception as e:
            logger.warning(f"Error estimating gas: {e}.")
            raise e

    async def send_transaction(
            self,
            to: str,
            data: str,
            value: int = 0,
            chain_id: Optional[int] = None,
    ) -> str:
        if chain_id is None:
            chain_id = await self.web3.eth.chain_id

        # Get gas estimate
        tx_params = {
            "from": self.wallet_address,
            "to": to,
            "data": data,
            "value": value,
            "chainId": chain_id,
        }

        try:
            gas_limit = await self.estimate_gas(tx_params)
            tx_params["gas"] = gas_limit
        except Exception as e:
            raise e

        # Get gas price params
        gas_params = await self.get_gas_params()
        tx_params.update(gas_params)

        # Get nonce
        tx_params["nonce"] = await self.web3.eth.get_transaction_count(self.wallet_address)

        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(tx_params, self.private_key)
        tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return tx_hash.hex()


    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def swap_tokens(
            self,
            token_in_address: str,
            token_out_address: str,
            amount_in: int,
            min_amount_out: int,
    ):
        try:
            # Определяем символы токенов для логов
            token_in_symbol = next(
                (
                    k
                    for k, v in TOKENS.items()
                    if v["address"].lower() == token_in_address.lower()
                ),
                "Unknown",
            )
            token_out_symbol = next(
                (
                    k
                    for k, v in TOKENS.items()
                    if v["address"].lower() == token_out_address.lower()
                ),
                "Unknown",
            )

            amount_in_readable = amount_in / 10 ** 18
            logger.info(
                f" | Swapping {amount_in_readable:.4f} {token_in_symbol} -> {token_out_symbol}"
            )

            # Проверяем баланс
            native_balance = await self.get_wallet_balance(is_native=True)
            if native_balance == 0:
                raise Exception("Native token balance is 0")

            # Апрув токена
            router_address = ROUTER_ADDRESS
            chain_id = await self.web3.eth.chain_id

            # Используем максимальное значение uint256 для неограниченного апрува
            await self.approve_token(
                token_address=token_in_address,
                spender_address=router_address,
                amount=MAX_UINT256,  # Unlimited approval
                chain_id=chain_id,
                token_abi=ERC_20_ABI,
                explorer_url=EXPLORER_URL_0G,
            )

            # Параметры свапа
            swap_params = {
                "tokenIn": token_in_address,
                "tokenOut": token_out_address,
                "fee": 3000,  # 0.3%
                "recipient": self.wallet_address,
                "deadline": int(time.time()) + 1800,  # +30 минут
                "amountIn": amount_in,
                "amountOutMinimum": min_amount_out,
                "sqrtPriceLimitX96": 0,
            }

            # Кодируем функцию и параметры
            function_signature = "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))"
            function_selector = SyncWeb3.keccak(text=function_signature)[:4]

            encoded_params = abi.encode(
                [
                    "address",
                    "address",
                    "uint24",
                    "address",
                    "uint256",
                    "uint256",
                    "uint256",
                    "uint160",
                ],
                [
                    swap_params["tokenIn"],
                    swap_params["tokenOut"],
                    swap_params["fee"],
                    swap_params["recipient"],
                    swap_params["deadline"],
                    swap_params["amountIn"],
                    swap_params["amountOutMinimum"],
                    swap_params["sqrtPriceLimitX96"],
                ],
            )

            encoded_data = function_selector + encoded_params

            # Отправляем транзакцию свапа
            tx_hash = await self.send_transaction(
                to=router_address,
                data=encoded_data,
                chain_id=chain_id,
            )

            receipt = await self.web3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=240,
            )

            if receipt["status"] == 1:
                logger.success(
                    f"Successfully swapped {amount_in_readable:.4f} {token_in_symbol} -> {token_out_symbol}"
                    f" Explorer URL: {EXPLORER_URL_0G}{tx_hash}"
                )
                return tx_hash
            else:
                raise Exception("Swap transaction failed")

        except Exception as e:
            random_pause = random.randint(3, 30)
            logger.error(
                f"Failed to swap tokens: {str(e)}. Sleeping {random_pause} seconds..."
            )
            await asyncio.sleep(random_pause)
            raise


    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def execute_swap(self):
        native_balance = await self.get_wallet_balance(is_native=True)
        eth_balance = Web3.from_wei(native_balance, 'ether')
        logger.info(f"{round(float(eth_balance), 4)} $0g")

        if native_balance == 0:
            logger.error(f'[{self.wallet_address}] | Native balance is 0.')
            return None

        # Получаем балансы всех трех токенов
        token_balances = {}
        for symbol, token_data in TOKENS.items():
            balance = await self.get_token_balance(
                wallet_address=self.wallet_address,
                token_address=token_data["address"],
                token_abi=ERC_20_ABI,
                decimals=token_data["decimals"],
                symbol=symbol,
            )
            token_balances[symbol] = balance.wei
            logger.info(
                f" {symbol} Balance: {balance.wei / 10 ** 18:.4f}"
            )

        # Проверяем, есть ли токены с балансом
        tokens_with_balance = [
            symbol for symbol, balance in token_balances.items() if balance > 0
        ]

        if not tokens_with_balance:
            raise Exception("No tokens with balance available for swaps")

        # Выбираем случайный токен для свапа из тех, где есть баланс
        token_in_symbol = random.choice(tokens_with_balance)
        token_in_balance = token_balances[token_in_symbol]
        token_in_address = TOKENS[token_in_symbol]["address"]

        # Выбираем токен для получения (только USDT если входящий ETH или BTC, иначе ETH или BTC)
        if token_in_symbol == "USDT":
            available_out_tokens = ["ETH", "BTC"]
            token_out_symbol = random.choice(available_out_tokens)
        else:
            # Если входящий токен ETH или BTC, то выходящий только USDT
            token_out_symbol = "USDT"

        token_out_address = TOKENS[token_out_symbol]["address"]

        # Определяем процент баланса для свапа
        swap_percent = random.randint(5, 10)

        # Рассчитываем сумму для свапа
        amount_to_swap = int(token_in_balance * swap_percent / 100)

        logger.info(
            f"Swapping {swap_percent}% of {token_in_symbol} ({amount_to_swap / 10 ** 18:.4f}) -> {token_out_symbol}"
        )

        # Выполняем свап
        await self.swap_tokens(
            token_in_address=token_in_address,
            token_out_address=token_out_address,
            amount_in=amount_to_swap,
            min_amount_out=0,
        )


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
