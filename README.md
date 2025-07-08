# NAT シミュレーター

これは、Network Address Translation (NAT) の動作をシミュレートするシンプルなTUI (Text-based User Interface) アプリケーションです。内部ネットワークからの通信がどのようにNATデバイスによって外部ネットワークへ変換され、そのエントリがどのように管理されるかを視覚的に確認できます。

なお、NATテーブルエントリは通常300秒以上のTTLのようですが、シミュレーションのためにTTLを30秒に設定しています。これにより、エントリの追加や削除の動作を短時間で確認できます。

下記のasciinemaにて動作は見られると思います。

<a href="https://asciinema.org/a/akIaiJCttzErzzHgLAJgncESy?autoplay=1" target="_blank"><img src="https://asciinema.org/a/akIaiJCttzErzzHgLAJgncESy.svg" /></a>



## 想定するネットワーク構成

```mermaid
graph TD
    subgraph "Internal Network (192.168.10.0/16)" # ここを修正
        A[Internal Host 192.168.10.X]
    end

    subgraph NAT Router
        B(Internal Interface 192.168.10.1)
        C(External Interface 203.0.113.1)
    end

    subgraph Internet
        D[External Server 8.8.8.8]
    end

    A -- Request (192.168.10.X:Port -> 8.8.8.8:Port) --> B
    C -- Translated Request (203.0.113.1:NewPort -> 8.8.8.8:Port) --> D
    D -- Response (8.8.8.8:Port -> 203.0.113.1:NewPort) --> C
    B -- Translated Response (8.8.8.8:Port -> 192.168.10.X:Port) --> A
```

## これは何か

本シミュレーターは、以下の機能を備えています。

*   **TUI表示**: `textual` ライブラリを使用したテキストベースのユーザーインターフェースで、NATテーブルの状態をリアルタイムに表示します。
*   **NATテーブル管理**: SQLite3データベースを使用してNATエントリを永続化します。エントリには内部送信元IP/ポート、宛先IP/ポート、外部送信元IP/ポート、およびTTL (Time To Live) が含まれます。
*   **通信シミュレーション**: 
    *   ユーザーが宛先IPアドレスとポートを入力することで、手動でNAT変換をトリガーできます。
    *   バックグラウンドでランダムな内部ホストからの通信が自動的に生成され、NATテーブルにエントリが追加・更新されます。
    *   既存の通信が継続している場合、対応するNATエントリのTTLがリフレッシュされます。
*   **TTL管理**: エントリのTTLは1秒ごとに減少し、TTLが0になったエントリは自動的に削除されます。TTLが短いエントリは赤色、リフレッシュされたエントリは緑色で表示され、視覚的なフィードバックを提供します。

## 起動方法

本シミュレーターはPythonで記述されており、`uv` を使用して依存関係を管理しています。

1.  **`uv` のインストール**:
    `uv` がインストールされていない場合は、[uvの公式サイト](https://docs.astral.sh/uv/) を参照してインストールしてください。

2.  **仮想環境と依存関係のセットアップ**
    プロジェクトのルートディレクトリで以下のコマンドを実行します。

    ```bash
    uv venv
    uv sync
    ```

3.  **NATテーブルの初期化**(任意/必要に応じて):
    シミュレーターを初めて起動する前、またはNATテーブルをリセットしたい場合は、以下のコマンドを実行します。
    なおこの操作をしなくても、NATテーブルは初回起動時に自動生成されます。

    ```bash
    uv run python main.py --init
    ```

4.  **シミュレーターの起動**:
    以下のコマンドでシミュレーターを起動します。

    ```bash
    uv run python main.py
    ```

## 基本的な使い方

シミュレーターが起動すると、TUIが表示されます。

*   **宛先IP:ポートの入力**: 画面下部の入力フィールドに、通信したい宛先のIPアドレスとポートを `IPアドレス:ポート番号` の形式で入力し、`Enter` キーを押してください (例: `8.8.8.8:53`)。
*   **NATテーブル**: 画面上部のテーブルに、NATエントリが表示されます。
    *   `Internal Src IP`: 内部ネットワークの送信元IPアドレス (シミュレーターが自動生成または固定)
    *   `Internal Src Port`: 内部ネットワークの送信元ポート (シミュレーターが自動生成)
    *   `Dest IP`: 宛先IPアドレス
    *   `Dest Port`: 宛先ポート
    *   `External Src IP`: NATデバイスの外部IPアドレス (固定: `203.0.113.1`)
    *   `External Src Port`: NATデバイスが割り当てた外部ポート
    *   `TTL`: エントリの残り寿命 (秒)。TTLがリフレッシュされると緑色、残り少ないと赤色で表示されます。
*   **通知**: 画面右下には、新しいNATエントリの追加や期限切れエントリの削除に関する通知が表示されます。
*   **ダークモードの切り替え**: `d` キーを押すと、ダークモードとライトモードを切り替えられます。
*   **終了**: `q` キーを押すと、アプリケーションを終了します。
* **コマンドパレット**: `Ctrl+P` を押すと、コマンドパレットが開きます。ここからダークモードの切り替えや終了などの操作が可能です。
    * 個人的に終了はこの操作(`Ctrl+P` → `Quit`)が一番使いやすいと思います。

# 開発環境

- macOS Sequela(M4)
- [Python](https://www.python.org/) 3.13.4
- [uv](https://docs.astral.sh/uv/) 0.7.19
- 開発の補助に[Gemini-cli](https://cloud.google.com/blog/ja/topics/developers-practitioners/introducing-gemini-cli)(8割flash)を使用しています、というかtextual周辺はほぼこいつにお任せです

# ライセンス

こちらのコードは、**GPL v3**として公開します。

このプロジェクトは [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html) のもとで公開されています。詳細は `LICENSE` ファイルをご覧ください。

と思ったのですが、なぜか今www.gnu.orgに繋がらないので後ほど追加する予定です。 -> [追加しました](./LICENSE)

# お願い

もしこのコードやツールが使えそう、どこかで使いたいというときは、ぜひご連絡ください。 **もしよければGitHubのスターをつけていただけると嬉しいです**。
