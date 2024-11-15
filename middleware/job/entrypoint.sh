#!/bin/bash
cron
python app.py
tail -f /var/log/cron.log
