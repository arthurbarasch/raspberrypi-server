# Raspberry Pi GPIO Server

This server runs on your Raspberry Pi Zero W to enable remote GPIO control via HTTP requests.

## Installation on Raspberry Pi

1. Copy this folder to your Raspberry Pi Zero W:

   ```bash
   scp -r raspberry-pi-server pi@raspberrypi.local:~/
   ```

2. SSH into your Raspberry Pi:

   ```bash
   ssh pi@raspberrypi.local
   ```

3. Install dependencies:
   ```bash
   cd ~/raspberry-pi-server
   pip3 install -r requirements.txt
   ```

## Running the Server

### Manual Start

```bash
python3 gpio_server.py
```

### Run as a Service (Auto-start on boot)

1. Create a systemd service file:

   ```bash
   sudo nano /etc/systemd/system/gpio-server.service
   ```

2. Add the following content:

   ```ini
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

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable gpio-server
   sudo systemctl start gpio-server
   ```

4. Check status:
   ```bash
   sudo systemctl status gpio-server
   ```

## API Endpoints

### Set GPIO Pin State

```bash
POST http://raspberrypi.local:3001/gpio/set
Content-Type: application/json

{
  "gpio": 17,
  "state": true
}
```

### Get GPIO Status

```bash
GET http://raspberrypi.local:3001/gpio/status
```

### Set GPIO Mode

```bash
POST http://raspberrypi.local:3001/gpio/mode
Content-Type: application/json

{
  "gpio": 17,
  "mode": "input"
}
```

### Health Check

```bash
GET http://raspberrypi.local:3001/health
```

## Valid GPIO Pins (BCM Numbering)

2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 22, 23, 24, 25, 27

## Troubleshooting

- Make sure the server is accessible on your network
- Check firewall settings if you can't connect
- Verify GPIO permissions (user needs to be in gpio group):
  ```bash
  sudo usermod -a -G gpio pi
  ```
