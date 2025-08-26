
import asyncio
import random
import subprocess
import os

import src.utils
import src.model

from loguru import logger

from core.database.db import WalletDatabase
from src.utils.logs import ProgressTracker, create_progress_tracker

async def process():
    async def launch_wrapper(index, proxy, account_data):
        async with semaphore:
            await account_flow(
                index,
                proxy,
                account_data,
                config,
                lock,
                progress_tracker,
            )

    # print("Available options:\n")
    # print("[1] 😈 Start farm")
    # # print("[2] 🔧 Edit config")
    # # print("[3] 🔍 Balance checker")
    # # print("[4] 🔄 Update")
    # print("[5] 👋 Exit")
    #
    # try:
    #     choice = input("Enter option (1-5): ").strip()
    # except Exception as e:
    #     logger.error(f"Input error: {e}")
    #     return
    # if choice == "5" or not choice:
    #     return
    # elif choice == "1":
    #     pass

    config = src.utils.get_config()

    # Читаем все файлы
    proxies = src.utils.read_txt_file("proxies", "data/proxies.txt")
    if len(proxies) == 0:
        logger.error("No proxies found in data/proxies.txt")
        return
    proxies = src.utils.check_proxy_format(proxies)
    if proxies is False:
        return

    db = WalletDatabase()
    accounts_to_process = db.get_active_private_keys()
    # accounts_to_process = ', '.join(str(x) for x in accounts)
    # accounts_to_process = private_keys[start_index - 1: end_index]

    shuffled_indices = list(range(len(accounts_to_process)))
    random.shuffle(shuffled_indices)

    lock = asyncio.Lock()
    threads = config.SETTINGS.THREADS

    cycled_proxies = [
        proxies[i % len(proxies)] for i in range(len(accounts_to_process))
    ]

    semaphore = asyncio.Semaphore(value=threads)

    tasks = []

    # Создаем трекер прогресса перед созданием задач
    total_accounts = len(accounts_to_process)
    progress_tracker = await create_progress_tracker(
        total=total_accounts, description="Accounts completed"
    )

    start_index = 1

    for shuffled_idx in shuffled_indices:
        tasks.append(
            asyncio.create_task(
                launch_wrapper(
                    start_index + shuffled_idx,
                    cycled_proxies[shuffled_idx],
                    accounts_to_process[shuffled_idx],
                    # discord_tokens[shuffled_idx],
                    # twitter_tokens[shuffled_idx],
                    # emails[shuffled_idx],
                )
            )
        )

    await asyncio.gather(*tasks)


async def account_flow(
    account_index: int,
    proxy: str,
    account_data: str,
    # discord_token: str,
    # twitter_token: str,
    # email: str,
    config: src.utils.config.Config,
    lock: asyncio.Lock,
    progress_tracker: ProgressTracker,
):
    try:
        name = account_data[0]
        pause = random.randint(
            config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[0],
            config.SETTINGS.RANDOM_INITIALIZATION_PAUSE[1],
        )
        logger.info(f"[{name}:{account_index}] Sleeping for {pause} seconds before start...")
        await asyncio.sleep(pause)

        report = False

        instance = src.model.Start(
            account_index, proxy, account_data, config
        )

        result = await wrapper(instance.initialize, config)
        if not result:
            report = True

        result = await wrapper(instance.flow, config)
        if not result:
            report = True

        pause = random.randint(
            config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACCOUNTS[0],
            config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACCOUNTS[1],
        )
        logger.info(f"Sleeping for {pause} seconds before next account...")
        await asyncio.sleep(pause)

        # В конце функции, независимо от результата, обновляем прогресс
        await progress_tracker.increment(1)

    except Exception as err:
        logger.error(f"[{name}:{account_index}] | Account flow failed: {err}")
        # Даже если произошла ошибка, все равно считаем аккаунт обработанным
        await progress_tracker.increment(1)


async def wrapper(function, config: src.utils.config.Config, *args, **kwargs):
    attempts = config.SETTINGS.ATTEMPTS
    for attempt in range(attempts):
        result = await function(*args, **kwargs)
        if isinstance(result, tuple) and result and isinstance(result[0], bool):
            if result[0]:
                return result
        elif isinstance(result, bool):
            if result:
                return True

        if attempt < attempts - 1:  # Don't sleep after the last attempt
            pause = random.randint(
                config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
            )
            logger.info(
                f"Sleeping for {pause} seconds before next attempt {attempt+1}/{config.SETTINGS.ATTEMPTS}..."
            )
            await asyncio.sleep(pause)

    return result
