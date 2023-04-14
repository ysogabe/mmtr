import sys
import threading
import os
import configparser
import signal
import socket
import json

from time import sleep
from datetime import datetime

from bluepy.btle import Scanner, DefaultDelegate
from azure.eventhub import EventHubProducerClient, EventData

# 設定ファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini")

# Azure Event Hubs 接続情報
CONNECTION_STR = os.environ.get(
    "AZURE_CONNECTION_STR", config.get("azure_eventhubs", "connection_str")
)
EVENTHUB_NAME = os.environ.get(
    "AZURE_EVENTHUB_NAME", config.get("azure_eventhubs", "eventhub_name")
)

# MAMORIOのUUID
MAMORIO_UUID = "b9407f30f5f8466eaff925556b57fe6e"
IBEACON_PREFIX = "4c000215"


class ScanDelegate(DefaultDelegate):
    """
    BLEデバイスの検出イベントを処理するためにBluePyのDefaultDelegateクラスを継承したクラスです。
    """

    def __init__(self):
        DefaultDelegate.__init__(self)

    def ibeacon_tx_power_to_dbm(self, hex_value: str) -> int:
        """
        このメソッドは、iBeaconのトランスミット電力値（hex_value）をデシベルミリワット（dBm）に変換します。

        :param hex_value: 16進数形式のiBeaconトランスミット電力値
        :type hex_value: str
        :return: dBm 単位のトランスミット電力
        :rtype: int
        """

        # 16進数の値を10進数に変換
        decimal_value = int(hex_value, 16)

        # 10進数が128以上の場合、256を引いて負の値に変換
        if decimal_value >= 128:
            tx_power_dbm = decimal_value - 256
        else:
            # それ以外の場合は、そのままの値を利用
            tx_power_dbm = decimal_value

        return tx_power_dbm

    def hex_to_little_endian_decimal(self, hex_value: str) -> int:
        """
        リトルエンディアンの16進数値を10進数に変換します。

        :param hex_value: str, 16進数値
        :return: int, 与えられた16進数値から変換された10進数値
        """

        # Reverse byte order for little endian
        little_endian_hex = ''.join(reversed([hex_value[i:i + 2] for i in range(0, len(hex_value), 2)]))

        # Convert hexadecimal to decimal
        decimal_value = int(little_endian_hex, 16)

        return decimal_value

    def handleDiscovery(self, dev, isNewDev, isNewData):
        """
        BLEデバイスが検出された際に呼び出されるメソッドです。
        iBeaconのデータを処理し、MAMORIOが検出された場合はイベントハブにデータを送信します。

        :param dev: 発見されたデバイスに関する詳細を含むデバイスオブジェクト
        :param isNewDev: True の場合、新規検出デバイスです
        :param isNewData: True の場合、デバイスから新しいデータを受信しました
        """

        try:
            current_time = datetime.now()
            if isNewDev or isNewData:
                for (adtype, desc, value) in dev.getScanData():
                    if adtype == 255 and value.startswith(IBEACON_PREFIX):
                        uuid = value[8:40]
                        major = self.hex_to_little_endian_decimal(value[40:44])
                        minor = self.hex_to_little_endian_decimal(value[44:48])
                        tx = self.ibeacon_tx_power_to_dbm(value[48:50])
                        print(f"uuid: {uuid}, major: {major}, minor: {minor}, tx: {tx}, RSSI: {dev.rssi}, RAW: {value}")

                        if uuid.lower() == MAMORIO_UUID.lower():
                            sender_thread = threading.Thread(target=self.send_to_eventhubs, args=(dev.addr, dev.rssi), daemon=True)
                            sender_thread.start()
                            sender_thread.join()
        except Exception as e:
            print(f"Error occurred in handleDiscovery: {e}")
            raise e

    def send_to_eventhubs(self, beacon_addr, rssi):
        """
        検出されたiBeaconのデータをAzure Event Hubsに送信します。追加のデータとして、送信時刻と送信ホスト名も含まれます。

        :param beacon_addr: str, 検出されたビーコンのアドレス
        :param rssi: int, 検出されたビーコンの信号強度（RSSI）
        """

        try:
            producer = EventHubProducerClient.from_connection_string(conn_str=CONNECTION_STR, eventhub_name=EVENTHUB_NAME)

            # 現在の時刻とホスト名を取得
            timestamp = datetime.utcnow().isoformat()
            host_name = socket.gethostname()

            # データをJSON形式に変換
            data = {
                "MAMORIO": beacon_addr,
                "RSSI": rssi,
                "Time": timestamp,
                "Hostname": host_name
            }

            event_data = EventData(json.dumps(data))
            producer.send_batch([event_data])
        except Exception as e:
            print(f"Error occurred during sending to Event Hubs: {e}")
        finally:
            if 'producer' in locals():
                producer.close()

            
def signal_handler(sig, frame):
    """
    シグナルハンドラ: この関数は、特定のシグナルを受信したときに実行されます。

    引数:
        sig: 受信したシグナルの型（信号番号）
        frame: 現在実行中のスタックフレーム

    処理内容:
        1. "終了処理中..."というメッセージを表示します。
        2. プログラムを終了し、終了ステータス0でシステムに終了を通知します。
    """
    print("終了処理中...")
    sys.exit(0)

    
# シグナルハンドラを登録
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C用（キーボード割り込み）
signal.signal(signal.SIGTERM, signal_handler)  # killコマンド用（終了要求）


def start_scanning():
    """
    BLEデバイスの連続的なスキャンを開始します。
    """

    scanner = Scanner().withDelegate(ScanDelegate())
    
    try:
        while True:
            devices = scanner.scan(5.0)
    except Exception as e:
        print(f"Error occurred in start_scanning: {e}")
        sys.exit()

        
if __name__ == "__main__":
    # スキャニング用のスレッドを作成して実行
    scan_thread = threading.Thread(target=start_scanning, daemon=True)
    scan_thread.start()

    # 無限ループ中にシグナルを待つ
    try:
        while True:
            sleep(1)
    except (KeyboardInterrupt, SystemExit):  # キーボード割り込みやシステム終了で終了処理
        sys.exit()
