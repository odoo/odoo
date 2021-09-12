import os,time,sys,shutil
import random, string
import json
import subprocess
import imp,re,shutil
import argparse
import logging
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
        _logger.info("Couldn't connect remote %r"%e)
        raise e

def isdbaccessible(details):
    _logger.info("Recieved Request %r"%locals())
    try:
        psycopg2.connect(
                dbname="postgres",
                user=details['user'],
                password=details['password'],
                host=details['host'],
                port=details['port'])
        return True
    except Exception as e:
        _logger.info("Error while connecting DB :-%r"%e)
        print("Error while connecting DB :-%r"%e)
        raise e
