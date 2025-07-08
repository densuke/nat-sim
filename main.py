import argparse
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log, Input, Button, DataTable
from textual.containers import Container
from textual.reactive import var
from textual.screen import Screen
from textual.message import Message
import ipaddress
import random
import time # ここを追加
from rich.text import Text # ここを追加

from nat_table import NATTable

class NATSimulatorApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    CSS_PATH = "nat_simulator.css"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nat_table = NATTable()
        self._active_sessions = {} # {(internal_src_ip, internal_src_port, dest_ip, dest_port): last_active_timestamp}
        self.communication_duration = 15 # seconds
        self.reuse_probability = 0.7

    def compose(self) -> ComposeResult:
        with Container():
            yield Header()
            yield DataTable()
            yield Input(placeholder="Enter destination IP:Port (e.g., 8.8.8.8:53)", id="address_input") # プレースホルダーを変更
            yield Button("Translate", id="translate_button")
            yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self.update_nat_table_display()
        self.set_interval(1, self.decrement_ttl_and_clean_table)
        self.set_interval(1, self.generate_random_nat_entry) # 2秒から1秒に変更

    def update_nat_table_display(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Internal Src IP", "Internal Src Port", "Dest IP", "Dest Port", "External Src IP", "External Src Port", "TTL") # カラム名を変更
        for entry in self.nat_table.get_all_entries():
            # TTLの値を取得
            ttl = entry[6]
            ttl_text = str(ttl)

            # TTLの値に基づいて色を決定
            if ttl >= 25: # TTLが初期値に近い場合 (例: 30秒の8割以上)
                ttl_text = Text(ttl_text, style="green")
            elif ttl <= 3: # TTLが残り3秒以下の場合
                ttl_text = Text(ttl_text, style="red")
            else:
                ttl_text = Text(ttl_text) # デフォルトの色

            # 新しい行データを作成 (TTLを色付きテキストに置き換え)
            row_data = list(entry)
            row_data[6] = ttl_text
            table.add_row(*row_data)

    def decrement_ttl_and_clean_table(self) -> None:
        deleted_entries = self.nat_table.delete_expired_entries()
        for entry in deleted_entries:
            self.notify(f"Expired entry deleted: {entry[0]}:{entry[1]} -> {entry[2]}:{entry[3]} (External: {entry[4]}:{entry[5]})", severity="error")
        self.nat_table.decrement_ttl()
        self.update_nat_table_display()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "address_input":
            self.translate_address()

    def translate_address(self) -> None:
        input_widget = self.query_one(Input)
        dest_address_port = input_widget.value.strip() # 変数名を変更
        input_widget.value = ""

        if not dest_address_port:
            self.notify("Please enter a destination IP:Port.", severity="warning")
            return

        try:
            dest_ip, dest_port_str = dest_address_port.split(":") # 変数名を変更
            dest_port = int(dest_port_str) # 変数名を変更
        except ValueError:
            self.notify("Invalid format. Please use IP:Port (e.g., 8.8.8.8:53).", severity="error")
            return

        # 宛先IPアドレスのバリデーション
        try:
            ipaddress.IPv4Address(dest_ip)
        except ipaddress.AddressValueError:
            self.notify(f"Invalid destination IP address format: {dest_ip}", severity="error")
            return

        # 宛先ポートのバリデーション
        if not (0 <= dest_port <= 65535):
            self.notify(f"Invalid destination port number: {dest_port}. Port must be between 0 and 65535.", severity="error")
            return

        # 内部送信元IPアドレスとポートを生成
        internal_src_ip = "192.168.10.100" # 固定の内部送信元IPアドレス
        internal_src_port = random.randint(49152, 65535) # エフェメラルポートの範囲でランダム生成

        # NATデバイスの外部IPアドレス (固定)
        external_ip_for_nat = "203.0.113.1"

        entry = self.nat_table.get_or_create_entry(internal_src_ip, internal_src_port, dest_ip, dest_port, external_ip_for_nat)
        if entry:
            self.notify(f"Translated: {entry[0]}:{entry[1]} -> {entry[2]}:{entry[3]} (External: {entry[4]}:{entry[5]}) (TTL: {entry[6]})", severity="information")
            self.update_nat_table_display()
        else:
            self.notify("Failed to translate address.", severity="error")

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_quit(self) -> None:
        self.exit()

    def generate_random_nat_entry(self) -> None:
        current_time = time.time()

        # アクティブでないセッションをクリーンアップ
        sessions_to_remove = []
        for session_key, last_active_time in self._active_sessions.items():
            if current_time - last_active_time > self.communication_duration:
                sessions_to_remove.append(session_key)
        for session_key in sessions_to_remove:
            del self._active_sessions[session_key]

        # 既存エントリを再利用する確率
        if random.random() < self.reuse_probability and self._active_sessions:
            # 既存のアクティブなセッションを再利用
            session_key = random.choice(list(self._active_sessions.keys()))
            internal_src_ip, internal_src_port, dest_ip, dest_port = session_key
            action_type = "Reused"
        else:
            # 新しいエントリを生成
            internal_src_ip = str(ipaddress.IPv4Address(random.randint(ipaddress.IPv4Address('192.168.10.1').__int__(), ipaddress.IPv4Address('192.168.10.254').__int__()))) # 192.168.10.x の範囲でランダム生成
            internal_src_port = random.randint(49152, 65535) # エフェメラルポートの範囲でランダム生成
            dest_ip = str(ipaddress.IPv4Address(random.randint(ipaddress.IPv4Address('1.0.0.0').__int__(), ipaddress.IPv4Address('223.255.255.255').__int__()))) # Public IP range
            dest_port = random.randint(1, 65535)
            action_type = "New"

        external_ip_for_nat = "203.0.113.1" # 固定のNATデバイスの外部IP

        entry = self.nat_table.get_or_create_entry(internal_src_ip, internal_src_port, dest_ip, dest_port, external_ip_for_nat)
        if entry:
            # セッションの最終活動時刻を更新
            session_key = (entry[0], entry[1], entry[2], entry[3])
            self._active_sessions[session_key] = current_time
            # 新規エントリの場合のみ通知
            if action_type == "New":
                self.notify(f"{action_type} entry: {entry[0]}:{entry[1]} -> {entry[2]}:{entry[3]} (External: {entry[4]}:{entry[5]}) (TTL: {entry[6]})", severity="information")
            self.update_nat_table_display()
        else:
            self.notify("Failed to process entry.", severity="error")

def main():
    parser = argparse.ArgumentParser(description="NAT Simulator")
    parser.add_argument("--init", action="store_true", help="Initialize NAT table")
    args = parser.parse_args()

    if args.init:
        print("Initializing NAT table...")
        nat_table = NATTable()
        nat_table.initialize_table()
        nat_table.close()
        print("NAT table initialized.")
    else:
        app = NATSimulatorApp()
        app.run()

if __name__ == "__main__":
    main()