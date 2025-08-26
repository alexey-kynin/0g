from loguru import logger
import primp
import random
import asyncio


from src.model.pharos_xyz.instance import PharosXYZ


from src.utils.config import Config
from src.utils.client import create_client


class Start:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        account_data: str,
        # discord_token: str,
        # twitter_token: str,
        # email: str,
        config: Config,
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.account_data = account_data
        self.name = account_data[0]
        # self.discord_token = discord_token
        # self.twitter_token = twitter_token
        # self.email = email
        self.config = config

        self.session: primp.AsyncClient | None = None

    async def initialize(self):
        try:
            self.session = await create_client(self.proxy)

            return True
        except Exception as e:
            logger.error(f"[{self.account_index}] | Error: {e}")
            return False

    async def flow(self):
        try:
            pharos = PharosXYZ(
                self.account_index,
                self.proxy,
                self.account_data,
                # self.discord_token,
                self.config,
                self.session,
            )


            # if "farm_faucet" in self.config.FLOW.TASKS:
            #     await plume.faucet()
            #     return True

            # Заранее определяем все задачи
            planned_tasks = []
            task_plan_msg = []
            task_index = 1  # Initialize a single counter for all tasks

            #Подготовка TASKS
            for task_item in self.config.FLOW.TASKS:
                if isinstance(task_item, list):
                    # For tasks in square brackets [], randomly select one
                    selected_task = random.choice(task_item)
                    planned_tasks.append((task_index, selected_task, "random_choice"))
                    task_plan_msg.append(f"{task_index}. {selected_task}")
                    task_index += 1
                elif isinstance(task_item, tuple):
                    # For tasks in parentheses (), shuffle and execute all
                    shuffled_tasks = list(task_item)
                    random.shuffle(shuffled_tasks)

                    # Add each shuffled task individually to the plan
                    for subtask in shuffled_tasks:
                        planned_tasks.append((task_index, subtask, "shuffled_item"))
                        task_plan_msg.append(f"{task_index}. {subtask}")
                        task_index += 1
                else:
                    planned_tasks.append((task_index, task_item, "single"))
                    task_plan_msg.append(f"{task_index}. {task_item}")
                    task_index += 1

            # Выводим план выполнения одним сообщением
            logger.info(
                f"[{self.name}:{self.account_index}] Task execution plan: {' | '.join(task_plan_msg)}"
            )

            # Выполняем задачи по плану
            for i, task, task_type in planned_tasks:
                logger.info(f"[{self.name}:{self.account_index}] Executing task {i}: {task}")
                await self.execute_task(task, pharos)
                await self.sleep(task)

            return True
        except Exception as e:
            # import traceback
            # traceback.print_exc()
            # input()
            logger.error(f"[{self.account_index}] | Error: {e}")
            return False



    async def execute_task(self, task, pharos):
        """Execute a single task"""
        task = task.lower()

        if task == "chekin":
            await pharos.chekin()

        # elif task == "zenith":
        #     zenith = Zenithfinance(
        #         self.account_index,
        #         self.proxy,
        #         self.account_data,
        #         self.config,
        #         self.session,
        #     )
        #     await zenith.swap()




    async def sleep(self, task_name: str):
        """Делает рандомную паузу между действиями"""
        pause = random.randint(
            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
            self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
        )
        logger.info(
            f"[{self.name}:{self.account_index}] Sleeping {pause} seconds after {task_name}"
        )
        await asyncio.sleep(pause)
