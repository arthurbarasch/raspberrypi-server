git clone https://github.com/arthurbarasch/raspberrypi-server.git

cd ~/raspberrypi-server
pip3 install -r requirements.txt

sudo nano /etc/systemd/system/gpio-server.service

```
   [Unit]
   Description=GPIO Control Server
   After=network.target

   [Service]
   Type=simple
   User=arthur
   WorkingDirectory=/home/arthur/raspberrypi-server
   ExecStart=/usr/bin/python3 /home/arthur/raspberrypi-server/gpio_server.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
```

sudo systemctl daemon-reload
sudo systemctl enable gpio-server
sudo systemctl start gpio-server
