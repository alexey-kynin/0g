from web3 import AsyncWeb3
from eth_account import Account
import asyncio
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import random, json
from loguru import logger
# from src.utils.constants import RPC_URL, EXPLORER_URL, ERC20_ABI

from eth_utils import keccak
from src.utils.constants import RPCS_PLUME, EXPLORER_URL, ERC20_ABI
from src.model.pharos_xyz.constants import PLUME_CHAIN_ID, IZUMI_PLUME_ABI, PLUME_TOKENS, IZUMI_CONTRACT, PLUME_TOKENS, IZUMI_PLUME_CONTRACT
import time
from src.utils.config import Config
from src.utils.constants import EXPLORER_URL, RPCS_PLUME, CONTRACT_ADDRESSES_PLUME
from pathlib import Path


class Raffle:
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
        self.router_contract = self.web3.eth.contract(
            address=AsyncWeb3.to_checksum_address(IZUMI_PLUME_CONTRACT), abi=IZUMI_PLUME_ABI
        )
        self.FEE_TIER = 10000  # 1%
        self.config = config

        self._nonce_lock = asyncio.Lock()
        self._nonce = None

        self.raffle_address = CONTRACT_ADDRESSES_PLUME['raffle']
        self.spin_address = CONTRACT_ADDRESSES_PLUME['spin']

        self.ABI_PATH = Path(__file__).resolve().parent.parent.parent.parent / "abi" / "plume_contract_abi.json"
        with open(self.ABI_PATH , "r") as f:
            self.contract_abi = json.load(f)

        self.contract_spin = self.web3.eth.contract(address=self.spin_address, abi=self.contract_abi)


    async def get_prize_ids(self):
        contract = self.web3.eth.contract(
            address=AsyncWeb3.to_checksum_address(self.raffle_address),
            abi=[{"inputs": [], "name": "getPrizeIds",
                  "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
                  "stateMutability": "view", "type": "function"}],
        )
        ids = await contract.functions.getPrizeIds().call()
        return ids


    async def get_calldata(self, prizeld, another_value):
        method_id = "bce5d97b"

        prize_id_padded = hex(prizeld)[2:].rjust(64, "0")
        another_value_padded = hex(another_value)[2:].rjust(64, "0")

        return "0x" + method_id + prize_id_padded + another_value_padded


    async def get_user_data(self) -> dict:
        """Вызов getUserData(user) и возврат данных в словаре."""
        try:

            result = await self.contract_spin.functions.getUserData(self.account.address).call()
            daily_streak, last_spin_ts, jackpot_wins, raffle_tickets_gained, raffle_tickets_balance, pp_gained, small_plume_tokens = result

            return {
                "dailyStreak": daily_streak,
                "lastSpinTimestamp": last_spin_ts,
                "jackpotWins": jackpot_wins,
                "raffleTicketsGained": raffle_tickets_gained,
                "raffleTicketsBalance": raffle_tickets_balance,
                "ppGained": pp_gained,
                "smallPlumeTokens": small_plume_tokens
            }

        except Exception as e:
            print(f"Error fetching user data: {e}")
            return {}


    async def get_nonce(self):
        nonce = None
        async with self._nonce_lock:
            if self._nonce is None:
                self._nonce = await self.web3.eth.get_transaction_count(self.account.address)
            else:
                self._nonce += 1
            nonce = self._nonce

        return nonce


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

    async def get_gas_params(self) -> Dict[str, int]:
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]

        # Для Layer1 Ethereum или совместимых сетей обычно priorityFee ≈ 1–2 Gwei
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


    async def add_tickets(self):
        percent = 11
        prizelds = await self.get_prize_ids()
        prizeld = random.choice(prizelds)

        user_data = await self.get_user_data()
        raffleTicketsBalance = user_data['raffleTicketsBalance']
        if not raffleTicketsBalance or raffleTicketsBalance == 0:
            logger.info("No tickets available to participate")
            return None

        another_value = round(raffleTicketsBalance * (percent / 100))

        calldata = await self.get_calldata(prizeld, another_value)

        nonce = await self.get_nonce()

        gas_params = await self.get_gas_params()

        tx_data = {
            "chainId": PLUME_CHAIN_ID,
            "from": self.account.address,
            "to": AsyncWeb3.to_checksum_address(self.raffle_address),
            "data": calldata,
            **gas_params,
            "nonce": nonce
        }

        estimate_gas = await self.estimate_gas(tx_data)
        tx_data["gas"] = estimate_gas

        print(estimate_gas)

        return await self.execute_transaction(tx_data)




