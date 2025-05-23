from flask import Flask, render_template, request, jsonify, session
import mysql.connector
import random

# pykakasi をインポート
from pykakasi import kakasi

app = Flask(__name__)
# セッション管理のために秘密鍵を設定。
# 本番では予測困難な非常に長い文字列に置き換えてください！
app.secret_key = '11233' # <<< ここを置き換えてください！ <<<

# kakasi のインスタンスを初期化
kks = kakasi() 

# 変換モードを設定
# ここでそれぞれの変換を設定し、結果はひらがなになるようにします
# 'J' (漢字) から 'H' (ひらがな)
# 'K' (カタカナ) から 'H' (ひらがな)
# 'H' (ひらがな) から 'H' (ひらがな)
kks.setMode("J", "H") # 漢字をひらがなに
kks.setMode("K", "H") # カタカナをひらがなに
kks.setMode("H", "H") # ひらがなをひらがなに（念のため）
# kks.setMode("a", "H") # ローマ字をひらがなに - この行はコメントアウトまたは削除
# kks.setMode("nr", "H") # 数字をひらがなに - この行はコメントアウトまたは削除

# 変換器を取得
converter = kks.getConverter()


# --- データベース接続設定 ---
# MySQLのユーザー名、パスワード、ホスト名、データベース名を設定
DB_CONFIG = {
    'user': 'root', # あなたのMySQLユーザー名
    'password': '0627', # <<< ここをあなたのMySQL rootユーザーのパスワードに置き換えてください！ <<<
    'host': '127.0.0.1', # MySQLサーバーのホスト名 (WSL2内で動いている場合は127.0.0.1)
    'database': 'shiritori_db', # 作成したデータベース名
    'port': 3306 # MySQLのデフォルトポート
}

# データベース接続を管理するヘルパー関数
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"データベース接続エラー: {err}")
        return None

# ゲーム終了時にデータベースの used フラグをリセットする関数
# ページロード時や新しいゲーム開始時に呼び出されます。
def reset_used_words_in_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE words SET used = FALSE WHERE used = TRUE")
            conn.commit()
            print("すべての単語の 'used' フラグをリセットしました。")
        except mysql.connector.Error as err:
            print(f"データベースのusedフラグのリセット中にエラー: {err}")
        finally:
            cursor.close()
            conn.close()

# --- ゲームの状態管理（セッションを使用） ---

@app.route('/')
def index():
    # ページがロードされるたびに、セッションとデータベースのusedフラグをリセット
    # これにより、常に新しいゲームが始まるようにします（開発・デバッグ用）
    session['used_words'] = []
    session['last_word_notation'] = ''
    session['game_over'] = False 
    reset_used_words_in_db() 

    # CPUの最初の単語を決定し、セッションとデータベースに記録
    # (session['last_word_notation'] が常に空になるようにしたので、条件はシンプルに)
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True) # 辞書形式で結果を取得
        # 「り」で始まる単語をランダムに選択
        # CSVの「表記」が「り」または「リ」で始まるものを検索
        cursor.execute("""
            SELECT heading, notation FROM words
            WHERE used = FALSE
            ORDER BY RAND() LIMIT 1 
        """)
        first_cpu_word = cursor.fetchone()
        cursor.close()
        conn.close()

        if first_cpu_word:
            cpu_word_heading = first_cpu_word['heading']
            cpu_word_notation = first_cpu_word['notation'] # 例: 'リトマス試験紙' (漢字を含む表記)
            
            # --- ここにデバッグ用のprint文を詳しく追加 ---
            print(f"\n--- CPU初期単語デバッグ情報 ---")
            print(f"選ばれたCPU単語 (heading): {cpu_word_heading}")
            print(f"選ばれたCPU単語 (notation): {cpu_word_notation}")
            print(f"notationの長さ: {len(cpu_word_notation)}")
            
            # ここが一番重要: 表記全体をひらがな化
            full_notation_hira = converter.do(cpu_word_notation) # 例: 'リトマス試験紙' -> 'りとますしけんし'
            
            print(f"表記全体をひらがな化: '{full_notation_hira}'")
            
            # ひらがな化した文字列の最後の文字を取得
            if len(full_notation_hira) > 0:
                last_char_for_shiritori = full_notation_hira[-1] # 例: 'りとますしけんし' -> 'し'
                print(f"しりとり用最終文字 (ひらがな化後の最後の文字): '{last_char_for_shiritori}'")
            else:
                last_char_for_shiritori = ""
                print("ERROR: ひらがな化した表記が空です！")
            
            print(f"--- デバッグ情報ここまで ---\n")
            # --- デバッグ用のprint文の追加はここまで ---

            session['used_words'].append(cpu_word_heading)
            # 最後の単語の表記を保存（ひらがな化）
            session['last_word_notation'] = full_notation_hira[-1] # <<< ここを修正済み >>>
            
            # データベースの単語を使用済みに更新
            conn = get_db_connection() # 新しい接続を取得
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE words SET used = TRUE WHERE heading = %s AND notation = %s",
                               (cpu_word_heading, cpu_word_notation))
                conn.commit()
                cursor.close()
                conn.close()
            else:
                return "データベース接続エラー: CPUの初期単語を設定できませんでした。", 500

            # テンプレートに最初のCPUの単語を渡す
            return render_template('index.html', initial_cpu_word={'heading': cpu_word_heading, 'notation': cpu_word_notation})
        else:
            return "ゲームを開始するための「り」から始まる単語が見つかりませんでした。データベースを確認してください。", 500
    else:
        return "データベース接続エラー: 初期単語の取得に失敗しました。", 500


@app.route('/play_word', methods=['POST'])
def play_word():
    try:
        data = request.get_json()
        user_word = data['word'].strip() # 前後の空白を除去

        # ゲームが初期化されていない、または終了している場合はエラー
        if 'used_words' not in session or 'last_word_notation' not in session or session.get('game_over', False):
            return jsonify({'success': False, 'message': 'ゲームが初期化されていないか、終了しています。ページをリロードして新しいゲームを開始してください。'}), 400

        # --- ユーザー単語のバリデーション ---
        # 1. 空白チェック
        if not user_word:
            return jsonify({'success': False, 'message': '単語を入力してください。'}), 400

        # 2. 直前の単語の最後の文字から始まっているか
        # 入力単語の最初の文字をひらがな化
        user_word_hira_first_char = converter.do(user_word[0]) 
        
        # デバッグログは前回確認済みなので削除してもOK
        # print(f"DEBUG: ユーザー単語: {user_word}")
        # print(f"DEBUG: ユーザー単語の最初の文字: {user_word[0]}")
        # print(f"DEBUG: converter.do(user_word[0]) の結果: {user_word_hira_first_char}")
        # print(f"DEBUG: session['last_word_notation'] (期待される次の文字): {session['last_word_notation']}")


        # データベースに登録されている表記がひらがな以外で、最後の文字が特殊な場合（例：っ、ー）は
        # 正しく次の文字を判定できない可能性がある。
        # 今回は簡易的に、表記の最後の文字をそのまま変換して使用
        if session['last_word_notation'] and user_word_hira_first_char != session['last_word_notation']:
            return jsonify({'success': False, 'message': f"前の単語の最後の文字「{session['last_word_notation']}」から始まる単語を入力してください。"}), 400

        # 3. 「ん」で終わっていないか
        # 入力単語の最後の文字をひらがな化してチェック
        last_char_of_user_word_hira = converter.do(user_word[-1])
        if last_char_of_user_word_hira == 'ん':
            session['game_over'] = True
            return jsonify({'success': True, 'game_over': True, 'message': f"あなたの負けです！「{user_word}」は「ん」で終わります。"}), 200

        # 4. データベースに存在する有効な単語か、かつ未使用か
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'データベース接続エラー。'}), 500
        
        cursor = conn.cursor(dictionary=True)
        # ユーザーの入力単語を検索（見出し、表記の両方で検索）
        cursor.execute("""
            SELECT heading, notation, used FROM words
            WHERE heading = %s OR notation = %s
        """, (user_word, user_word))
        found_word = cursor.fetchone()

        if not found_word:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'その単語は辞書にありません。'}), 400

        if found_word['used']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': f"「{user_word}」は既に使用されています。別の単語を入力してください。"}), 400

        # ユーザーの単語を使用済みにマークし、履歴に追加
        session['used_words'].append(found_word['heading'])
        cursor.execute("UPDATE words SET used = TRUE WHERE heading = %s AND notation = %s",
                       (found_word['heading'], found_word['notation']))
        conn.commit()

        # 最後の単語の表記を更新
        # <<< ここを修正済み >>>
        full_found_notation_hira = converter.do(found_word['notation'])
        session['last_word_notation'] = full_found_notation_hira[-1]

        # --- CPUの単語選択ロジック ---
        # ユーザーの単語の最後の文字を取得（ひらがな化）
        last_char_of_user_word_for_cpu = session['last_word_notation']
        
        # CPUが「ん」で終わる単語を選んだ場合、ゲームオーバーになるので除外
        # また、使用済みの単語も除外
        # LIKE句は単語の冒頭文字が部分一致するものを検索します。
        # %s はプレースホルダで、後で値がバインドされます。
        cpu_query_param = last_char_of_user_word_for_cpu + '%'
        cursor.execute("""
            SELECT heading, notation FROM words
            WHERE (notation LIKE %s OR heading LIKE %s)
              AND (notation NOT LIKE '%%ん' AND notation NOT LIKE '%%ン'
                   AND heading NOT LIKE '%%ん' AND heading NOT LIKE '%%ン') -- 「ん」で終わる単語は除外
              AND used = FALSE
            ORDER BY RAND() LIMIT 1
        """, (cpu_query_param, cpu_query_param))
        
        cpu_selected_word = cursor.fetchone()
        cursor.close()
        conn.close()

        if cpu_selected_word:
            cpu_word_heading = cpu_selected_word['heading']
            cpu_word_notation = cpu_selected_word['notation']

            # CPUの単語をセッションのused_wordsに追加
            session['used_words'].append(cpu_word_heading)
            # データベースの単語を使用済みに更新
            conn = get_db_connection() # 新しい接続を取得
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE words SET used = TRUE WHERE heading = %s AND notation = %s",
                               (cpu_word_heading, cpu_word_notation))
                conn.commit()
                cursor.close()
                conn.close()
            else:
                return jsonify({'success': False, 'message': 'データベース接続エラー: CPUの単語を更新できませんでした。'}), 500

            # 最後の単語の表記を更新
            # <<< ここを修正済み >>>
            full_cpu_notation_hira = converter.do(cpu_word_notation)
            session['last_word_notation'] = full_cpu_notation_hira[-1]

            return jsonify({
                'success': True,
                'message': '単語を受け取りました。',
                'user_word': user_word,
                'cpu_word': cpu_word_heading, # CPUの単語を返送
                'game_over': False
            }), 200

        else:
            # CPUが返答できない場合（有効な単語がない、またはすべて使用済み）
            session['game_over'] = True
            return jsonify({
                'success': True,
                'game_over': True,
                'message': f"CPUは「{last_char_of_user_word_for_cpu}」から始まる単語を見つけられませんでした。あなたの勝ちです！"
            }), 200

    except Exception as e:
        print(f"エラー: {e}")
        # デバッグのためにエラーの詳細を返すことも可能だが、本番では非推奨
        return jsonify({
            'success': False,
            'message': 'サーバーエラーが発生しました。',
            'error': str(e)
        }), 500

# 降参ボタンのルート（POSTリクエストを受け付ける）
@app.route('/give_up', methods=['POST'])
def give_up():
    session['game_over'] = True
    # 降参時もデータベースの used フラグをリセットするのが一般的
    reset_used_words_in_db() 
    return jsonify({
        'success': True,
        'game_over': True,
        'message': 'あなたが降参しました。ゲーム終了です。'
    }), 200

if __name__ == '__main__':
    app.run(debug=True)