# BLE MAMORIO Scanner and Azure Event Hubs Sender

本プロジェクトは、MAMORIOデバイスをBLE（Bluetooth Low Energy）でスキャンし、検出されたデータをAzure Event Hubsに送信するプログラムです。

## 前提条件

- Python 3.7 以上
- [bluepy](https://github.com/IanHarvey/bluepy) ライブラリ
- [azure-eventhub](https://pypi.org/project/azure-eventhub/) ライブラリ

以下のコマンドで必要なパッケージをインストールできます。

```bash
pip install bluepy azure-eventhub
```

RASPBERRY PI LITEにインストールする場合、以下のコマンドを実行して下さい。

```bash
sudo apt-get install -y python3-pip git build-essential libglib2.0-dev
sudo pip3 install bluepy azure-eventhub
```

## 設定

設定ファイル`config.ini`に以下の内容を記入してください。サンプルファイルは`config.ini.sample`です。

```ini
[azure_eventhubs]
connection_str = <your_connection_string>
eventhub_name = <your_eventhub_name>
```

Azure Event Hubsの接続文字列とEvent Hub名を`<your_connection_string>`および`<your_eventhub_name>`に置き換えてください。

また、環境変数`AZURE_CONNECTION_STR`および`AZURE_EVENTHUB_NAME`に同じ値を設定することもできます。

## 実行方法

このスクリプトではBLE（Bluetooth Low Energy）デバイスをスキャンするために、`bluepy`ライブラリを使用しています。`bluepy`ライブラリはLinux環境で動作し、一部の機能は特権ユーザー（rootユーザー）として実行する必要があります。

したがって、本プログラムを実行する際は、`sudo`コマンドを使って特権ユーザーとして実行することをお勧めします。以下のコマンドでプログラムを実行できます。

```bash
sudo python mmtr.py
```
プログラムはBLEデバイスをスキャンし、MAMORIOが検出されると、そのデータをAzure Event Hubsに送信します。

## サービス登録（Systemd）

Linuxシステムでは、 **Systemd** を利用してPythonスクリプトをデーモン化できます。まず、次のような新しいSystemdサービスファイルを作成してください(例：`/etc/systemd/system/mmtr.service`):

```
[Unit]
Description=BLE MAMORIO Scanner and Azure Event Hubs Sender

[Service]
User=root
WorkingDirectory=/path/to
ExecStart=/usr/bin/python3 /path/to/mmtr.py
Restart=always

[Install]
WantedBy=multi-user.target
```

上記ファイルでパスやユーザー名を適切に指定し、Systemdに新しいサービスを読み込ませて起動します:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mmtr.service
sudo systemctl start mmtr.service
```

## Dockerでの実行

このスクリプトではBLE（Bluetooth Low Energy）デバイスをスキャンするために、`bluepy`ライブラリを使用しています。`bluepy`ライブラリはLinux環境で動作し、一部の機能は特権ユーザー（rootユーザー）として実行する必要があります。

したがって、dockerで実行する場合、`--privileged` オプションを用いてホスト側へのアクセスを許可する必要があります。以下に実行例を記載します。


```bash
docker run -d --net host --privileged --restart always -v ${PWD}/config.ini:/app/src/config.ini pptdxsoliag/mmtr:0.0.1
```

なお、`--restart always` は`bluepy`ライブラリのエラー対策です。（調査中）

```
Error occurred in start_scanning: Failed to execute management command 'scan'
```

## 注意事項

本プログラムは、Linux環境で動作することを前提としています。WindowsやmacOSでは動作しない可能性があります。
開発環境はRaspberry PiなどのLinuxベースのシステムを推奨します。

ただし、`sudo`を使うとシステム内のすべてのリソースにアクセス可能となるため、必要以上にアクセス許可が与えられることを避けるため、最小限の権限で実行できるようにすることが望ましいです。そのため、`capabilities`を使用することで、必要な権限のみ付与することができます。以下の手順で`capabilities`を設定し、スクリプトを実行できます。

1. 実行ファイルに`setcap`コマンドで必要な権限を付与します。
   ```bash
   sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/bin/python3
   ```

   このコマンドはPython 3の実行ファイルに対して、必要な権限（`cap_net_raw`および`cap_net_admin`）を付与します。

2. スクリプトを通常のユーザー（`sudo`なし）で実行します。
   ```bash
   python main.py
   ```

注意: `setcap`コマンドによる権限付与はセキュリティ上のリスクがあるため、十分に注意して実施してください。信頼できるプログラムであることを確認した上で実行し、状況に応じてリスクを評価してください。