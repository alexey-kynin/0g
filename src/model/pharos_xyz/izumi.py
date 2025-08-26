from web3 import AsyncWeb3
from eth_account import Account
import asyncio
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import random
from loguru import logger
# from src.utils.constants import RPC_URL, EXPLORER_URL, ERC20_ABI

from eth_utils import keccak
from src.utils.constants import RPCS_PLUME, EXPLORER_URL, ERC20_ABI
from src.model.pharos_xyz.constants import PLUME_CHAIN_ID, IZUMI_PLUME_ABI, PLUME_TOKENS, IZUMI_CONTRACT, PLUME_TOKENS, IZUMI_PLUME_CONTRACT
import time
from src.utils.config import Config


class IzumiDex:
    def __init__(
        self, private_key: str, proxy: Optional[str] = None, config: Config = None
    ):
        self.web3 = AsyncWeb3(
             AsyncWeb3.AsyncHTTPProvider(
                 RPCS_PLUME,
                 request_kwargs={"proxy": (f"http://{proxy}"), "ssl": False},
             )
        )        
        self.account = Account.from_key(private_key)
        self.proxy = proxy

        self.router_address = AsyncWeb3.to_checksum_address(IZUMI_PLUME_CONTRACT)
        self.router_contract = self.web3.eth.contract(
            address=self.router_address, abi=IZUMI_PLUME_ABI
        )
        self.FEE_TIER = 10000  # 1%
        self.config = config


    async def get_gas_params(self) -> Dict[str, int]:
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]

        fallback_priority_gwei = 1.5

        try:
            priority_fee = await self.web3.eth.max_priority_fee
            if priority_fee == 0:
                priority_fee = AsyncWeb3.to_wei(fallback_priority_gwei, "gwei")
        except Exception:
            priority_fee = AsyncWeb3.to_wei(fallback_priority_gwei, "gwei")

        # Простой подход: maxFee = baseFee * 1.25 + priorityFee
        max_fee = int(base_fee * 1.25 + priority_fee)

        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
        }


    def convert_to_wei(self, amount: float, token: str) -> int:
        """Convert amount to wei based on token decimals."""
        if token == "native":
            return self.web3.to_wei(amount, "ether")
        decimals = PLUME_TOKENS[token.lower()]["decimals"]
        return int(Decimal(str(amount)) * Decimal(str(10**decimals)))


    def convert_from_wei(self, amount: int, token: str) -> float:
        """Convert wei amount back to token units."""
        if token == "native":
            return float(self.web3.from_wei(amount, "ether"))

        decimals = PLUME_TOKENS[token.lower()]["decimals"]

        return float(Decimal(str(amount)) / Decimal(str(10**decimals)))


    async def get_tokens_with_balance(self) -> List[Tuple[str, float]]:
        """Get list of tokens with non-zero balances."""
        tokens_with_balance = []

        # Check native token balance
        native_balance = await self.web3.eth.get_balance(self.account.address)
        if native_balance > 10**14:  # More than 0.0001 MON
            native_amount = float(self.web3.from_wei(native_balance, "ether"))
            tokens_with_balance.append(("native", native_amount))

        # Check other tokens
        for token in PLUME_TOKENS:
            if token == "wplume":  # Skip wplume as we handle it internally
                continue
            try:
                token_contract = self.web3.eth.contract(
                    address=AsyncWeb3.to_checksum_address(
                        PLUME_TOKENS[token]["address"]
                    ),
                    abi=ERC20_ABI,
                )
                balance = await token_contract.functions.balanceOf(
                    self.account.address
                ).call()

                # Only add tokens with sufficient balance (more than 0.0001 tokens)
                min_amount = 10 ** (PLUME_TOKENS[token]["decimals"] - 4)
                if balance >= min_amount:
                    decimals = PLUME_TOKENS[token]["decimals"]
                    amount = float(Decimal(str(balance)) / Decimal(str(10**decimals)))
                    tokens_with_balance.append((token, amount))

            except Exception as e:
                logger.error(f"Failed to get balance for {token}: {str(e)}")
                continue

        return tokens_with_balance


    async def approve_token(self, token: str, amount: int) -> Optional[str]:
        """Approve token spending for Izumi router."""
        try:
            token_contract = self.web3.eth.contract(
                address=AsyncWeb3.to_checksum_address(PLUME_TOKENS[token]["address"]),
                abi=ERC20_ABI,
            )

            current_allowance = await token_contract.functions.allowance(
                self.account.address, self.router_address
            ).call()

            if current_allowance >= amount:
                logger.info(f"Allowance sufficient for {token}")
                return None

            nonce = await self.web3.eth.get_transaction_count(self.account.address)
            gas_params = await self.get_gas_params()

            approve_tx = await token_contract.functions.approve(
                self.router_address, amount
            ).build_transaction(
                {
                    "from": AsyncWeb3.to_checksum_address(self.account.address),
                    "nonce": nonce,
                    "type": 2,
                    "chainId": PLUME_CHAIN_ID,
                    **gas_params,
                }
            )

            return await self.execute_transaction(approve_tx)

        except Exception as e:
            logger.error(f"Failed to approve {token}: {str(e)}")
            raise


    async def execute_transaction(self, transaction: Dict) -> str:
        """Execute a transaction and wait for confirmation."""
        signed_txn = self.web3.eth.account.sign_transaction(
            transaction, self.account.key
        )
        tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        logger.info("Waiting for transaction confirmation...")
        receipt = await self.web3.eth.wait_for_transaction_receipt(
            tx_hash, poll_latency=2
        )

        if receipt["status"] == 1:
            logger.success(
                f"Transaction successful! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}"
            )
            return tx_hash.hex()
        else:
            logger.error(
                f"Transaction failed! Explorer URL: {EXPLORER_URL}{tx_hash.hex()}"
            )
            raise Exception("Transaction failed")



    async def estimate_gas(self, tx_params: Dict) -> int:
        """Estimate gas for a transaction with a safety buffer."""
        try:
            # Create a copy of tx params without gas
            estimation_params = tx_params.copy()
            if "gas" in estimation_params:
                del estimation_params["gas"]


            # Estimate gas
            estimated_gas = await self.web3.eth.estimate_gas(estimation_params)

            # Add 20% safety buffer
            return int(estimated_gas * 1.05)
        except Exception as e:
            logger.warning(f"Gas estimation failed: {str(e)}")


    async def generate_swap_data(self, token_in: str, token_out: str, amount_in: int) -> Dict:
        """Generate swap tx data for Izumi correctly for all pairs"""
        try:
            token_in_address = (
                PLUME_TOKENS["wplume"]["address"] if token_in == "native" else PLUME_TOKENS[token_in]["address"]
            )
            token_out_address = (
                PLUME_TOKENS["wplume"]["address"] if token_out == "native" else PLUME_TOKENS[token_out]["address"]
            )

            # Encode path
            path = (
                    bytes.fromhex(token_in_address[2:])
                    + int(self.FEE_TIER).to_bytes(3, byteorder="big")
                    + bytes.fromhex(token_out_address[2:])
            )

            # deadline
            deadline = int(time.time()) + 6 * 3600
            min_acquired = 0
            out_fee = 500

            # Correct recipient
            if token_out == "native":
                recipient = AsyncWeb3.to_checksum_address(IZUMI_PLUME_CONTRACT)
            else:
                recipient = self.account.address

            params = (path, recipient, amount_in, min_acquired, out_fee, deadline)
            swap_data = self.router_contract.encode_abi("swapAmount", [params])

            multicall = [swap_data]

            # Если получаем native — нужно unwrap
            if token_out == "native":
                unwrap = self.router_contract.encode_abi(
                    "unwrapWETH9", [min_acquired, self.account.address]
                )
                multicall.append(unwrap)
                multicall.append(self.router_contract.encode_abi("refundETH"))

            # Если отправляем native — только refund
            elif token_in == "native":
                multicall.append(self.router_contract.encode_abi("refundETH"))


            multicall_data = self.router_contract.encode_abi("multicall", [multicall])

            value = amount_in if token_in == "native" else 0

            nonce = await self.web3.eth.get_transaction_count(self.account.address)
            gas_params = await self.get_gas_params()

            tx_data = {
                "chainId": PLUME_CHAIN_ID,
                "from": self.account.address,
                "to": AsyncWeb3.to_checksum_address(IZUMI_PLUME_CONTRACT),
                "value": value,
                "data": multicall_data,
                **gas_params,
                "nonce": nonce,
            }

            gas_limit = await self.estimate_gas(tx_data)
            tx_data["gas"] = gas_limit

            return tx_data

        except Exception as e:
            logger.error(f"Failed to generate swap data: {str(e)}")
            raise


    async def swap(self, percentage_to_swap: float, type: str = "swap") -> str:
        """Execute swap on Izumi DEX."""
        try:
            tokens_with_balance = await self.get_tokens_with_balance()

            if not tokens_with_balance:
                logger.info("No tokens with sufficient balance found to swap")
                return None

            # Regular swap
            # Pick random token with balance as input token
            token_in, balance = random.choice(tokens_with_balance)
            print(token_in, balance)

            # For output token, if input is native, pick any token except native
            # If input is a token, output must be native
            available_out_tokens = (
                [t for t in PLUME_TOKENS.keys() if t != "wplume"]
                if token_in == "native"
                else ["native"]
            )
            token_out = random.choice(available_out_tokens)
            print(token_out)

            # Calculate amount to swap based on direction
            if token_in == "native":
                # For native to token, use percentage
                actual_balance = await self.web3.eth.get_balance(
                    self.account.address
                )
                amount_wei = int(actual_balance * percentage_to_swap / 100)
                amount_token = float(self.web3.from_wei(amount_wei, "ether"))

            else:
                # Get actual balance directly in wei
                token_contract = self.web3.eth.contract(
                    address=AsyncWeb3.to_checksum_address(
                        PLUME_TOKENS[token_in]["address"]
                    ),
                    abi=ERC20_ABI,
                )

                amount_wei = await token_contract.functions.balanceOf(
                    self.account.address
                ).call()
                amount_wei = int(amount_wei * percentage_to_swap / 100)
                amount_token = self.convert_from_wei(amount_wei, token_in)

                # Approve token spending if not native
                # await self.approve_token(token_in, amount_wei)

                random_pause = random.randint(
                    self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
                    self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
                )
                logger.info(f"Sleeping {random_pause} seconds after approve")
                await asyncio.sleep(random_pause)

            logger.info(f"Swapping {amount_token} {token_in} to {token_out}")

            # Generate and execute swap transaction
            tx_data = await self.generate_swap_data(token_in, token_out, amount_wei)
            print(tx_data)

            # return await self.execute_transaction(tx_data)
            return 1
        #
        except Exception as e:
            logger.error(f"Izumi swap failed: {str(e)}")
            raise

    # async def get_pair_exists(self, token_a, token_b):
    #     # Проверяет, существует ли пара token_a и token_b в пуле через метод getPairState
    #     try:
    #         reserveA, reserveB, fee, pair =  self.router_contract.functions.getPairState(token_a, token_b).call()
    #         print(reserveA, reserveB, fee, pair)
    #         return pair != "0x0000000000000000000000000000000000000000"
    #     except Exception as e:
    #         print(f"❌ Ошибка при проверке пары: {e}")
    #         return False
    #
    # async def encode_path(token_in: str, fee: int, token_out: str) -> bytes:
    #     token_in_bytes = bytes.fromhex(token_in[2:] if token_in.startswith("0x") else token_in)
    #     token_out_bytes = bytes.fromhex(token_out[2:] if token_out.startswith("0x") else token_out)
    #     fee_bytes = fee.to_bytes(3, byteorder='big')
    #
    #     return token_in_bytes + fee_bytes + token_out_bytes
    #
    # async def swap(self, percentage_to_swap: float, type: str = "swap") -> str:
    #     """Execute swap on Izumi DEX."""
    #     try:
    #         tokens_with_balance = await self.get_tokens_with_balance()
    #
    #         if not tokens_with_balance:
    #             logger.info("No tokens with sufficient balance found to swap")
    #             return None
    #
    #         token_in, balance = random.choice(tokens_with_balance)
    #         print(token_in, balance)
    #
    #         available_out_tokens = (
    #             [t for t in PLUME_TOKENS.keys() if t != "wplume"]
    #             if token_in == "native"
    #             else ["native"]
    #         )
    #         token_out = random.choice(available_out_tokens)
    #         print(token_out)
    #
    #         if not await self.get_pair_exists(PLUME_TOKENS[token_in]["address"], PLUME_TOKENS[token_in]["address"]):
    #             print("❌ Пара токенов не найдена в пуле, операция отменена.")
    #             return None
    #
    #         # Calculate amount to swap based on direction
    #         if token_in == "native":
    #             # For native to token, use percentage
    #             actual_balance = await self.web3.eth.get_balance(
    #                 self.account.address
    #             )
    #             amount_wei = int(actual_balance * percentage_to_swap / 100)
    #             amount_token = float(self.web3.from_wei(amount_wei, "ether"))
    #
    #         else:
    #             token_contract = self.web3.eth.contract(
    #                 address=AsyncWeb3.to_checksum_address(
    #                     PLUME_TOKENS[token_in]["address"]
    #                 ),
    #                 abi=ERC20_ABI,
    #             )
    #
    #             amount_wei = await token_contract.functions.balanceOf(
    #                 self.account.address
    #             ).call()
    #             amount_wei = int(amount_wei * percentage_to_swap / 100)
    #             amount_token = self.convert_from_wei(amount_wei, token_in)
    #
    #             # Approve token spending if not native
    #             await self.approve_token(token_in, amount_wei)
    #
    #             random_pause = random.randint(
    #                 self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[0],
    #                 self.config.SETTINGS.PAUSE_BETWEEN_SWAPS[1],
    #             )
    #             logger.info(f"Sleeping {random_pause} seconds after approve")
    #             await asyncio.sleep(random_pause)
    #
    #             fee = 500
    #             path = self.encode_path(token_in, fee, token_out)
    #
    #
    #         #
    #         # logger.info(f"Swapping {amount_token} {token_in} to {token_out}")
    #         #
    #         # # Generate and execute swap transaction
    #         # tx_data = await self.generate_swap_data(token_in, token_out, amount_wei)
    #         # print(tx_data)
    #
    #         # return await self.execute_transaction(tx_data)
    #         return 1
    #     #
    #     except Exception as e:
    #         logger.error(f"Izumi swap failed: {str(e)}")
    #         raise
