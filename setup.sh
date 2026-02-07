#!/bin/bash
set -e

echo "=== Raspberry Pi GPIO Server Setup ==="

# Install Python dependencies
echo "Installing Python dependencies..."
cd ~/raspberrypi-server
pip3 install -r requirements.txt

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/gpio-server.service > /dev/null <<'EOF'
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
EOF

# Enable and start the service
echo "Enabling and starting gpio-server..."
sudo systemctl daemon-reload
sudo systemctl enable gpio-server
sudo systemctl start gpio-server

echo "=== Setup complete! ==="
echo "Check status with: sudo systemctl status gpio-server"
