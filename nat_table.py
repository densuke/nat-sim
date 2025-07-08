import sqlite3
import time
import random

class NATTable:
    def __init__(self, db_path="nat_table.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.initialize_table()

    def initialize_table(self):
        self.cursor.execute("DROP TABLE IF EXISTS nat_entries") # ここを追加
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS nat_entries (
                internal_src_ip TEXT NOT NULL,
                internal_src_port INTEGER NOT NULL,
                dest_ip TEXT NOT NULL,
                dest_port INTEGER NOT NULL,
                external_src_ip TEXT NOT NULL,
                external_src_port INTEGER NOT NULL,
                ttl INTEGER NOT NULL,
                PRIMARY KEY (internal_src_ip, internal_src_port, dest_ip, dest_port)
            )
        """)
        self.conn.commit()

    def add_entry(self, internal_src_ip, internal_src_port, dest_ip, dest_port, external_src_ip, external_src_port, ttl):
        self.cursor.execute("""
            INSERT OR REPLACE INTO nat_entries (internal_src_ip, internal_src_port, dest_ip, dest_port, external_src_ip, external_src_port, ttl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (internal_src_ip, internal_src_port, dest_ip, dest_port, external_src_ip, external_src_port, ttl))
        self.conn.commit()

    def get_entry(self, internal_src_ip, internal_src_port, dest_ip, dest_port):
        self.cursor.execute("""
            SELECT internal_src_ip, internal_src_port, dest_ip, dest_port, external_src_ip, external_src_port, ttl
            FROM nat_entries
            WHERE internal_src_ip = ? AND internal_src_port = ? AND dest_ip = ? AND dest_port = ?
        """, (internal_src_ip, internal_src_port, dest_ip, dest_port))
        return self.cursor.fetchone()

    def get_or_create_entry(self, internal_src_ip, internal_src_port, dest_ip, dest_port, external_ip_for_nat, initial_ttl=30): # 300から30に変更
        entry = self.get_entry(internal_src_ip, internal_src_port, dest_ip, dest_port)
        if entry:
            # エントリが存在する場合、TTLをリフレッシュ
            self.cursor.execute("""
                UPDATE nat_entries
                SET ttl = ?
                WHERE internal_src_ip = ? AND internal_src_port = ? AND dest_ip = ? AND dest_port = ?
            """, (initial_ttl, internal_src_ip, internal_src_port, dest_ip, dest_port))
            self.conn.commit()
            return self.get_entry(internal_src_ip, internal_src_port, dest_ip, dest_port) # 更新されたエントリを再取得
        else:
            external_src_port = self._get_next_available_external_port()
            self.add_entry(internal_src_ip, internal_src_port, dest_ip, dest_port, external_ip_for_nat, external_src_port, initial_ttl)
            return self.get_entry(internal_src_ip, internal_src_port, dest_ip, dest_port)

    def _get_next_available_external_port(self):
        self.cursor.execute("SELECT MAX(external_src_port) FROM nat_entries")
        max_port = self.cursor.fetchone()[0]
        if max_port is None:
            return 1024
        else:
            return max_port + 1

    def delete_expired_entries(self):
        self.cursor.execute("SELECT internal_src_ip, internal_src_port, dest_ip, dest_port, external_src_ip, external_src_port, ttl FROM nat_entries WHERE ttl <= 0")
        deleted_entries = self.cursor.fetchall()
        self.cursor.execute("DELETE FROM nat_entries WHERE ttl <= 0")
        self.conn.commit()
        return deleted_entries

    def decrement_ttl(self):
        self.cursor.execute("UPDATE nat_entries SET ttl = ttl - 1")
        self.conn.commit()

    def get_all_entries(self):
        self.cursor.execute("SELECT internal_src_ip, internal_src_port, dest_ip, dest_port, external_src_ip, external_src_port, ttl FROM nat_entries")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()