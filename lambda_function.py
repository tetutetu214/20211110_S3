import os
import sys
import logging

import boto3

from linebot import (LineBotApi, WebhookHandler)
from linebot.models import (MessageEvent, ImageMessage,TextSendMessage)
from linebot.exceptions import (LineBotApiError, InvalidSignatureError)

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

#1.LINEBOTと繋げるための記述
# 環境変数からline botのチャンネルアクセストークンとシークレットを読み込む
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

#無いならエラー
if channel_secret is None:
    logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

# apiとhandlerの生成（チャンネルアクセストークンとシークレットを渡す）
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# boto3を利用してS3連携
s3 = boto3.client("s3")
bucket = "20111110-s3"

#2.イベントからLINEBOT署名とボディ内容を受け取る

# Lambdaのメインファンクション
def lambda_handler(event, context):

    # 認証用のX-Line-Signatureヘッダー
    signature = event["headers"]["x-line-signature"]
    body = event["body"]

    # リターン値の設定
    ok_json = {"isBase64Encoded": False,
               "statusCode": 200,
               "headers": {},
               "body": ""}

    error_json = {"isBase64Encoded": False,
                  "statusCode": 403,
                  "headers": {},
                  "body": "Error"}

# 画像保存
    @handler.add(MessageEvent, message=ImageMessage)
    def message(line_event):

        # メッセージIDを抽出
        message_id = line_event.message.id

        # 画像ファイルを抽出
        message_content = line_bot_api.get_message_content(message_id)
        content = bytes()
        for chunk in message_content.iter_content():
            content += chunk

        # 画像ファイルを保存
        # key = "origin_photo/" + message_id + '.jpg'
        key = "2011/" + message_id + '.jpg'
        new_key = message_id[-3:]
        s3.put_object(Bucket=bucket, Key=key, Body=content)

        # 画像保存するとメッセージの返信
        line_bot_api.reply_message(line_event.reply_token,TextSendMessage(text='写真の保存に成功!'))

#例外処理としての動作
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        logger.error("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            logger.error("  %s: %s" % (m.property, m.message))
        return error_json
    except InvalidSignatureError:
        return error_json

    return ok_json