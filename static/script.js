// static/script.js

document.addEventListener('DOMContentLoaded', function () {
	console.log('しりとりアプリのJavaScriptがロードされました！');

	const shiritoriForm = document.getElementById('shiritori-form');
	const userWordInput = document.getElementById('user-word');
	const messagesDiv = document.getElementById('messages');
	const errorMessageP = document.getElementById('error-message');
	const giveUpButton = document.getElementById('give-up-button');

	// フォームが送信されたときの処理
	shiritoriForm.addEventListener('submit', async function (event) {
		event.preventDefault(); // デフォルトのフォーム送信動作（ページリロード）をキャンセル

		const userWord = userWordInput.value.trim(); // 入力された単語を取得し、前後の空白を除去
		if (userWord === '') {
			displayError('単語を入力してください。');
			return;
		}

		// エラーメッセージをリセット
		hideError();

		try {
			// Flaskの /play_word エンドポイントにPOSTリクエストを送信
			const response = await fetch('/play_word', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json' // 送信するデータの形式をJSONと指定
				},
				body: JSON.stringify({ word: userWord }) // 単語をJSON形式でボディに含める
			});

			const data = await response.json(); // サーバーからのJSONレスポンスを解析

			if (response.ok) { // HTTPステータスコードが200番台の場合
				if (data.game_over) {
					// ゲームオーバーの場合
					displayMessage(data.message);
					disableForm();
				} else {
					// ゲーム続行の場合
					addMessage('あなた', data.user_word); // ユーザーの単語を履歴に追加
					userWordInput.value = ''; // 入力欄をクリア
					addMessage('CPU', data.cpu_word); // CPUの単語を履歴に追加
				}
			} else { // HTTPステータスコードがエラー（4xx, 5xx）の場合
				displayError(data.message || '単語の送信に失敗しました。');
			}

		} catch (error) {
			console.error('通信エラー:', error);
			displayError('サーバーとの通信中にエラーが発生しました。');
		}
	});

	// 降参ボタンがクリックされたときの処理
	giveUpButton.addEventListener('click', async function () {
		if (confirm('本当に降参しますか？')) {
			try {
				const response = await fetch('/give_up', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					}
				});
				const data = await response.json();
				if (response.ok && data.game_over) {
					displayMessage(data.message);
					disableForm();
				} else {
					displayError(data.message || '降参処理に失敗しました。');
				}
			} catch (error) {
				console.error('降参通信エラー:', error);
				displayError('降参処理中にサーバーとの通信エラーが発生しました。');
			}
		}
	});

	// メッセージを履歴に追加するヘルパー関数
	function addMessage(sender, word) {
		const p = document.createElement('p');
		p.innerHTML = `<strong>${sender}:</strong> ${word}`;
		messagesDiv.appendChild(p);
		messagesDiv.scrollTop = messagesDiv.scrollHeight; // スクロールを最下部に移動
	}

	// エラーメッセージを表示するヘルパー関数
	function displayError(message) {
		errorMessageP.textContent = message;
		errorMessageP.style.display = 'block';
	}

	// エラーメッセージを非表示にするヘルパー関数
	function hideError() {
		errorMessageP.style.display = 'none';
		errorMessageP.textContent = '';
	}

	// ゲーム終了時にフォームを無効化するヘルパー関数
	function disableForm() {
		userWordInput.disabled = true;
		shiritoriForm.querySelector('button[type="submit"]').disabled = true;
		giveUpButton.disabled = true;
	}

	// 一般的なメッセージを表示するヘルパー関数
	function displayMessage(message) {
		const p = document.createElement('p');
		p.textContent = message;
		messagesDiv.appendChild(p);
		messagesDiv.scrollTop = messagesDiv.scrollHeight;
	}
});