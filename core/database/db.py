import sqlite3
import os
import random

from cryptography.fernet import Fernet
from eth_account import Account


class WalletDatabase:
    def __init__(self, db_name="wallets_0g.db", key_file="encryption.key"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_name = os.path.join(base_dir, db_name)
        self.key_file = os.path.join(base_dir, key_file)
        if not os.path.exists(self.key_file):
            raise FileNotFoundError(f"🔑 Файл ключа не найден: {self.key_file}")
        self.key = self.load_key()

    def generate_key(self):
        self.key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(self.key)
        print(f"🔐 Ключ шифрования сохранён в {self.key_file}")

    def load_key(self):
        with open(self.key_file, 'rb') as f:
            return f.read()

    def encrypt_private_key(self, private_key: str) -> str:
        cipher = Fernet(self.key)
        return cipher.encrypt(private_key.encode()).decode()

    def decrypt_private_key(self, encrypted_key: str) -> str:
        cipher = Fernet(self.key)
        return cipher.decrypt(encrypted_key.encode()).decode()

    def create_table(self):
        with sqlite3.connect(self.db_name) as conn:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    name TEXT,
                    wallet_address TEXT,
                    encrypted_private_key TEXT,
                    status INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
        print("📁 Таблица users создана")

    def add_user(self, name: str, wallet_address: str, private_key: str):
        encrypted_key = self.encrypt_private_key(private_key)
        with sqlite3.connect(self.db_name) as conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO users (name, wallet_address, encrypted_private_key, status)
                VALUES (?, ?, ?, 1)
            ''', (name, wallet_address, encrypted_key))
            conn.commit()
        print(f"✅ Пользователь {name} добавлен")


    def load_wallet_from_file(self, name: str, private_key: str):
        account = Account.from_key(private_key)
        self.add_user(name, account.address, private_key)

    def get_active_private_keys(self, random_user: bool = True):
        with sqlite3.connect(self.db_name) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name, wallet_address, "
                        "encrypted_private_key, inviteCode "
                        "FROM users WHERE status = 11")
            rows = cur.fetchall()

        if not rows:
            print("⚠️ Нет активных пользователей.")
            return []

        if random_user:
            random.shuffle(rows)  # Просто перемешиваем список

        result = []
        for name, wallet_address, encrypted_key, inviteCode in rows:
            try:
                decrypted = self.decrypt_private_key(encrypted_key)
                # print(f"🔓 Приватный ключ для {name}: {wallet_address}: {decrypted}")
                result.append((name, wallet_address, decrypted, inviteCode))
            except Exception as e:
                print(f"❌ Ошибка расшифровки ключа для {name}: {wallet_address}: {e}")
        return result


# # Пример использования
if __name__ == "__main__":
    db = WalletDatabase()
    db.load_wallet_from_file("kirillnaumenkov2", "0x90dc548f16cd2d127b41abc74ff07ffde94097be936660c779629622fcd60f23")

    # db.generate_key()
    # db.create_table()


