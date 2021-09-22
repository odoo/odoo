import os,time,sys,shutil
import random, string
import json
import subprocess
import imp,re,shutil
import argparse
import logging
import paramiko
import psycopg2
_logger = logging.getLogger(__name__)

def ishostaccessible(details):
    if details['server_type'] == "self":
        return True
    try:
        ssh_obj = paramiko.SSHClient()
        ssh_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_obj.connect(hostname = details['host'], username = details['user'], password = details['password'], port = details['port'])
        return ssh_obj
    except Exception as e:
        _logger.info("Couldn't connect remote%r"%e)
        raise e
class connect_exception(Exception):
    def __init__(self,message):
        print(message)





def isdbaccessible(host_server,db_server,config_path=None):
    try:
        ishostaccessible(host_server)
    except Exception as e:
        _logger.info("Remote Server not Reachable")
        raise e

    _logger.info("Recieved Request %r"%locals())
    details = db_server
    try:
        psycopg2.connect(
                dbname="postgres",
                user=details['user'],
                password=details['password'],
                host=details['host'],
                port=details['port'])
        _logger.info("Local Connection BUilt")
    except Exception as e:
        _logger.info("Error while connecting from local DB :-%r"%e)
        raise e
    if host_server['server_type'] == "self":
        return True
    try:
        ssh_obj = paramiko.SSHClient()
        ssh_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_obj.connect(hostname = host_server['host'], username = host_server['user'],password = host_server['password'], port = host_server['port'])
        sftp = ssh_obj.open_sftp()
        sftp.put(config_path+"/models/lib/connect_db.py",'/tmp/connect_db.py')
        sftp.close()

        cmd = "python3 -W ignore /tmp/connect_db.py  %r %r %r %r"%(details['user'], details['password'], details['host'], details['port'])
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_obj.exec_command(cmd)
        res = ssh_stdout.readlines()
        _logger.info("result = %r  %r"%(ssh_stderr.readlines(),res))

        if str(res[0].strip()) != "Yes":
            raise connect_exception("Connecting from Remote Host :- %r"%res)

    except Exception as e:
        _logger.info("Error while connecting from remote DB : %r"%e)
        raise e

