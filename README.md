しりとりWebアプリケーション
このプロジェクトは、PythonのFlaskフレームワークとMySQLデータベースを使用して構築された、シンプルなしりとりゲームのWebアプリケーションです。ユーザーとCPUの間でしりとりを楽しみます。

目次
機能
技術スタック
セットアップ方法
1. 前提条件
2. プロジェクトのクローンと移動
3. 仮想環境のセットアップ
4. Pythonの依存関係のインストール
5. MySQLデータベースの準備
6. 日本語単語データのインポート
7. Flaskアプリケーションの設定と実行
使い方
ファイル構造
今後の改善点 (任意)
機能
ユーザー入力: ユーザーが単語をフォームに入力して送信します。
CPUの返答: ユーザーの単語の最後の文字から始まる単語をデータベースから探し、ランダムに返答します。
しりとりルール:
単語は前の単語の最後の文字から始まる必要があります。
一度使用された単語は使えません。
「ん」で終わる単語は使えません（入力するとユーザーの負け）。
敗北条件:
ユーザーが「降参」ボタンを押した場合。
CPUが返答できる単語を見つけられなかった場合（ユーザーの勝ち）。
単語データベース: CSVファイルからインポートされた日本語単語データベースを使用します。
ひらがな/カタカナ/漢字変換: pykakasi ライブラリを使用して、単語の頭文字・末尾文字をひらがなに統一して判定します。
技術スタック
フロントエンド: HTML, CSS, JavaScript
バックエンド: Python (Flask)
データベース: MySQL
Python ライブラリ: mysql-connector-python, pykakasi
セットアップ方法
以下の手順でプロジェクトをローカル環境にセットアップし、実行できます。

1. 前提条件
Python: Python 3.8+ がインストールされていること。
pip: pip (Pythonのパッケージインストーラ) が利用できること。
MySQL Server: MySQL Server がインストールされ、起動していること (WSL2のUbuntu環境を推奨)。
2. プロジェクトのクローンと移動
まず、このリポジトリをクローンし、プロジェクトディレクトリに移動します。

Bash

git clone https://github.com/your-username/shiritori-app.git # あなたのリポジトリURLに置き換えてください
cd shiritori-app
3. 仮想環境のセットアップ
プロジェクトの依存関係を隔離するために、仮想環境を作成し、有効化します。

Bash

python3 -m venv venv
# Windowsの場合:
# .\venv\Scripts\activate
# Mac/Linux (WSL2)の場合:
source venv/bin/activate
4. Pythonの依存関係のインストール
必要なPythonライブラリをインストールします。

Bash

pip install Flask mysql-connector-python pykakasi wheel
もし pykakasi のインストールでエラーが出た場合は、pip install wheel を先に実行してから再度 pip install pykakasi を試してください。

5. MySQLデータベースの準備
MySQLデータベースを作成し、単語テーブルを構築します。

MySQLにログイン:
WSL2 (Ubuntu) のターミナルで以下を実行します。

Bash

sudo mysql
# または、パスワードを設定済みの場合は
# mysql -u root -p
データベースとテーブルの作成:
MySQLプロンプトで以下のSQLコマンドを実行します。

SQL

CREATE DATABASE shiritori_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shiritori_db;
CREATE TABLE words (
    id INT AUTO_INCREMENT PRIMARY KEY,
    heading VARCHAR(255) NOT NULL,
    notation VARCHAR(255) NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    UNIQUE(heading, notation)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
6. 日本語単語データのインポート
提供されたCSVファイル (japanese_words.csv を想定) をデータベースにインポートします。

japanese_words.csv の配置:
あなたのCSVファイルをプロジェクトのルートディレクトリ (shiritori-app/) に配置します。ファイル名が異なる場合は、後述の import_words.py 内の CSV_FILE_PATH を更新してください。
CSVの形式は「見出し,表記」で、エンコーディングは UTF-8 または UTF-8(BOM) が推奨されます。

import_words.py の作成:
プロジェクトのルートディレクトリに import_words.py というファイルを作成し、以下の内容を記述します。
DB_CONFIG の password を、あなたのMySQL root ユーザーのパスワードに置き換えてください。

Python

import csv
import mysql.connector
import os

DB_CONFIG = {
    'user': 'root',
    'password': 'your_mysql_root_password', # <<< ここをあなたのMySQL rootユーザーのパスワードに置き換えてください！ <<<
    'host': '127.0.0.1',
    'database': 'shiritori_db',
    'port': 3306
}

CSV_FILE_PATH = 'japanese_words.csv' # あなたのCSVファイル名に合わせてください
CSV_ENCODING = 'utf-8' # CSVファイルのエンコーディングに合わせてください ('shift_jis' など)

def import_words_to_db(csv_file, db_config, encoding='utf-8'):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INT AUTO_INCREMENT PRIMARY KEY,
                heading VARCHAR(255) NOT NULL,
                notation VARCHAR(255) NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                UNIQUE(heading, notation)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """)
        print("テーブル 'words' の存在を確認または作成しました。")

        with open(csv_file, 'r', encoding=encoding) as f:
            reader = csv.reader(f)
            next(reader) # ヘッダー行をスキップ

            insert_query = "INSERT IGNORE INTO words (heading, notation) VALUES (%s, %s)"
            word_count = 0
            for row in reader:
                if len(row) == 2:
                    heading = row[0].strip()
                    notation = row[1].strip()
                    try:
                        cursor.execute(insert_query, (heading, notation))
                        word_count += 1
                    except mysql.connector.Error as err:
                        if "Duplicate entry" in str(err):
                            # print(f"  -> この単語は既に存在します: {heading} ({notation})")
                            pass # 重複は無視
                        else:
                            print(f"単語 '{heading}' ({notation}) の挿入に失敗しました: {err}")
                else:
                    print(f"不正な形式の行をスキップ: {row}")

            conn.commit()
            print(f"データベースに {word_count} 件の単語を挿入または更新しました。")

    except mysql.connector.Error as err:
        print(f"MySQLエラー: {err}")
        print("データベース接続または操作に失敗しました。設定を確認してください。")
    except FileNotFoundError:
        print(f"エラー: '{csv_file}' が見つかりません。パスを確認してください。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("データベース接続を閉じました。")

if __name__ == '__main__':
    if DB_CONFIG['password'] == 'your_mysql_root_password':
        print("!!! 注意: 'import_words.py' の DB_CONFIG['password'] をあなたのMySQL rootユーザーのパスワードに置き換えてください。!!!")
    else:
        import_words_to_db(CSV_FILE_PATH, DB_CONFIG, CSV_ENCODING)
データインポートの実行:
仮想環境が有効な状態で、プロジェクトのルートディレクトリで以下を実行します。

Bash

python3 import_words.py
7. Flaskアプリケーションの設定と実行
app.py の配置と設定:
プロジェクトのルートディレクトリに app.py、templates/ ディレクトリ、static/ ディレクトリを配置します。
app.py の app.secret_key と DB_CONFIG の password を、ご自身の環境に合わせて置き換えてください。

Python

# app.py の全コード (上記で提供済みの最新版をコピーして貼り付けてください)
templates/ ディレクトリ内に index.html (UIのHTML)
static/ ディレクトリ内に style.css (UIのスタイル) と script.js (UIのロジック)
アプリケーションの実行:
仮想環境が有効な状態で、プロジェクトのルートディレクトリに移動し、以下を実行します。

Bash

python3 app.py
ブラウザでアクセス:
Webブラウザを開き、以下のURLにアクセスします。
http://127.0.0.1:5000/

これで、しりとりWebアプリケーションが開始されます。

使い方
ブラウザでアプリケーションにアクセスすると、CPUが「り」から始まる最初の単語を発言します。
入力フォームに、CPUの単語の最後の文字から始まる単語を入力し、「送信」ボタンを押します。
ルールに沿っていればCPUが返答し、ゲームが続行します。
ルール違反（「ん」で終わる、既出の単語など）の場合、エラーメッセージが表示されます。
CPUが返答できない場合、あなたの勝ちとなります。
いつでも「降参」ボタンを押してゲームを終了できます。
ファイル構造
shiritori-app/
├── venv/                   # Python仮想環境
├── app.py                  # Flaskアプリケーションのメインファイル
├── import_words.py         # CSVからDBへ単語をインポートするスクリプト
├── japanese_words.csv      # 日本語単語データ (見出し,表記 形式)
├── templates/
│   └── index.html          # HTMLテンプレート
└── static/
    ├── style.css           # CSSスタイルシート
    └── script.js           # JavaScriptロジック
今後の改善点 (任意)
最強モードの追加: CPUの単語選択ロジックを強化し、「る」攻めなどの戦略を実装する。
ゲームのリセット機能: 降参後やゲーム終了後に、UIから新しいゲームを簡単に開始できる機能を追加する。
デザインの改善: UI/UXをより洗練させる。
エラーハンドリングの強化: データベース接続エラーなど、ユーザーに分かりやすいメッセージを返す。
単語の読み仮名規則の厳密化: 小文字の拗音（ゃゅょ）や促音（っ）、長音（ー）などの特殊なルールを考慮する。
単語データ管理: 管理画面から単語を追加・編集できる機能など。
