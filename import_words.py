import csv
import mysql.connector # MySQLに接続するためのライブラリ
import os

# --- データベース接続設定 ---
# MySQLのユーザー名、パスワード、ホスト名、データベース名を設定
DB_CONFIG = {
    'user': 'root', # MySQLのユーザー名
    'password': '0627', # あなたのMySQL rootユーザーのパスワードに置き換えてください！
    'host': '127.0.0.1', # MySQLサーバーのホスト名 (WSL2内で動いている場合はlocalhost、外部から接続する場合はIPアドレス)
    'database': 'shiritori_db', # 作成したデータベース名
    'port': 3306 # MySQLのデフォルトポート
}

# CSVファイルのパス (スクリプトと同じディレクトリにある想定)
CSV_FILE_PATH = 'japanese_words.csv'
# CSVファイルのエンコーディング (UTF-8が一般的、Shift-JISの場合は 'shift_jis' または 'cp932')
CSV_ENCODING = 'utf-8' # 必要に応じて 'shift_jis' などに変更してください

def import_words_to_db(csv_file, db_config, encoding='utf-8'):
    conn = None
    cursor = None
    try:
        # MySQLに接続
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # テーブルが既に存在するか確認し、存在すれば単語データをクリア（デバッグ用）
        # 本番運用時は不要な場合が多い
        # cursor.execute("DROP TABLE IF EXISTS words;")
        # print("既存の 'words' テーブルを削除しました（もしあれば）。")

        # テーブルが存在しない場合は作成（初回のみ実行）
        # import_words_to_dbを複数回実行してもエラーにならないように
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

        # CSVファイルを読み込み、データベースに挿入
        with open(csv_file, 'r', encoding=encoding) as f:
            reader = csv.reader(f)
            next(reader) # ヘッダー行をスキップ

            # 挿入クエリ
            insert_query = "INSERT IGNORE INTO words (heading, notation) VALUES (%s, %s)"
            # IGNORE: UNIQUE制約に違反する重複行を無視して挿入を試みる

            word_count = 0
            for row in reader:
                if len(row) == 2: # 行が2つのカラム（見出し、表記）を持っていることを確認
                    heading = row[0].strip() # 前後の空白を除去
                    notation = row[1].strip()
                    try:
                        cursor.execute(insert_query, (heading, notation))
                        word_count += 1
                    except mysql.connector.Error as err:
                        print(f"単語 '{heading}' ({notation}) の挿入に失敗しました: {err}")
                        # UNIQUE制約違反などで失敗した場合でも処理を続行
                        if "Duplicate entry" in str(err):
                            print(f"  -> この単語は既に存在します: {heading} ({notation})")
                else:
                    print(f"不正な形式の行をスキップ: {row}")

            conn.commit() # 変更をコミットしてデータベースに保存
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
    # MySQLのパスワードを置き換えるのを忘れないでください！
    if DB_CONFIG['password'] == 'your_mysql_root_password':
        print("!!! 注意: 'import_words.py' の DB_CONFIG['password'] をあなたのMySQL rootユーザーのパスワードに置き換えてください。!!!")
    else:
        import_words_to_db(CSV_FILE_PATH, DB_CONFIG, CSV_ENCODING)