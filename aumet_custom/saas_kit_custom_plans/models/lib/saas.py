import os,time,sys,shutil
import random, string
import json
import subprocess
import imp,re,shutil
import argparse
import logging
from . import saas_remote
from . import saas_localhost

_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError as e:
    _logger.info("Paramiko Library not installed!!")

def isitaccessible(details):
    try:
        ssh_obj = paramiko.SSHClient()
        ssh_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_obj.connect(hostname = details['host'], username = details['user'], password = details['password'], port = details['port'])
        return ssh_obj
    except Exception as e:
        _logger.info("Couldn't connect remote%r"%e)
        return False

def main(context=None):
    _logger.info("Recieved Request %r"%locals())
    if context['host_server']['server_type'] == "self":
        _logger.info("On local Server")
        return saas_localhost.main(context)
    elif context['host_server']['server_type'] == "remote":
        if not isitaccessible(context['host_server']):
            _logger.info( str({"status": "Remote host not reachable"}))
            raise Exception("Remote Server not reachable")
        else:
            _logger.info("Connected")
        return saas_remote.main(context)

def create_db_template(db_template = None, modules = None, config_path = None, host_server = None, db_server = None):
    _logger.info("Recieved Request %r"%locals())
    if host_server.get('server_type') == "self":
        _logger.info("On local Server")
        return saas_localhost.create_db_template(**locals())
    elif host_server.get('server_type') == "remote":
        _logger.info("On remote Server")
        if not isitaccessible(host_server):
            _logger.info( str({"status": "Remote host not reachable"}))
            raise Exception("Remote Server not reachable")
        else:
            _logger.info("Connected")
        return saas_remote.create_db_template(**locals())
