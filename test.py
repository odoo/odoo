#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import threading
from requests import Session
try:
    if True:
        print('droping database')
        subprocess.run("dropdb test_concurrency_xdo > /dev/null 2>&1", shell=True)
        print('creating database')
        subprocess.run("python3 odoo-bin -d test_concurrency_xdo -i base,web --stop-after-init --skip-auto-install", shell=True)
        print('running odoo instances')

    p1 = subprocess.Popen("python3 odoo-bin -d test_concurrency_xdo --workers=1 --http-port 9069 --gevent-port 9169 --max-cron-thread=0".split(' '))
    p2 = subprocess.Popen("python3 odoo-bin -d test_concurrency_xdo --workers=1 --http-port 9070 --gevent-port 9170 --max-cron-thread=0".split(' '))

    s = Session()
    time.sleep(5)  # wait for servers to be up
    csrf_token = s.get('http://127.0.0.1:9069/web/login').text.split('name="csrf_token" value="')[1].split('"')[0]
    print(csrf_token)

    response = s.post('http://127.0.0.1:9069/web/login', data={
        'csrf_token': csrf_token,
        'login': 'admin',
        'password': 'admin',
        'type': 'password',
    })

    # _get_group_definitions should be warm at this

    # install module project

    url = 'http://127.0.0.1:9070/web/dataset/call_button/ir.module.module/button_immediate_install'
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "id": 6,
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "args": [[434]],  # project
            "kwargs": {
            },
            "method": "button_immediate_install",
            "model": "ir.module.module",
        },
    }

    def install_project():
        s.post(url, headers=headers, json=data)

    instal_thread = threading.Thread(target=install_project)
    instal_thread.start()


    for i in range(100):
        # looping will work because the cache is removed but in theory we need to wait for the install to be finished
        print()
        time.sleep(1)
        url = 'http://127.0.0.1:9069/web/dataset/call_kw/ir.model.access/get_access_groups'
        headers = {
            'content-type': 'application/json',
        }
        data = {
            "id": 23,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "ir.model.access",
                "method": "get_access_groups",
                "args": [[], 'res.partner', 'read'],
                "kwargs": {
                    "context": {},
                }
            }
        }
        response = s.post(url, headers=headers, json=data)
        print('access groups response:', response.status_code, response.text)

    instal_thread.join()
    p1.wait()

    response = s.post(url, headers=headers, json=data)

except Exception as e:
    print('error occurred:', e)

finally:
    print('killing odoo instances')
    os.killpg(0, signal.SIGKILL)