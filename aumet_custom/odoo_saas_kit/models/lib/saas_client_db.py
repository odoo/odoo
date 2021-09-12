import os,time,sys
import random, string
import json
import subprocess
import imp,re,shutil
import argparse
import logging
import functools

from collections import defaultdict
import socket

from contextlib import closing
#from . import pg_query
_logger = logging.getLogger(__name__)

#operation = "create" #clone/create


try:
    import docker
except ImportError as e:
    _logger.info("Docker Library not installed!!")
    
try:
    import erppeek
except ImportError as e:
    _logger.info("erppeek library not installed!!")
    

def check_error(func):
    functools.wraps(func)
    def wrapper(*args,**argc):
        try:
            return func(*args,**argc)
        except Exception as e:
            _logger.info("Error %s occurred at %s"%(str(e),func.__name__))
            return False
    return wrapper


def connect_db(url , database , user_name , passwd , flag = True):
    count = 0
    client = ""
    while count < 5: # Let me try 5 times not more
        try:
            _logger.info("Attempt %d %s."%(count,flag))
            if flag:
                client = erppeek.Client(server=str(url)) #Connect without specifying DB for creation of new.
            else:
                client = erppeek.Client(server=str(url),db = database, user = user_name,password = passwd) # connect specifically as new DB has to cloned. Need db's admin credentials
            break
        except Exception as e:
            _logger.info("Could not Connect. Error %s"%str(e))
            count += 1
            time.sleep(4)
    if count == 5:
        _logger.info("Maximum attempt made but couldn't connect")
        return False # Tried enough times, still couldn't connect.
    _logger.info("Connection built!! %s"%client)
    return client

@check_error
def cloning(client,database_name,admin_passwd):
    try:
        count = 0
        for each in range(5):
            res = client.clone_database(admin_passwd,database_name) #cloning DB using admin password 
            count += 1
            _logger.info("%s Attempt to clone!! %s"%(database_name,res))
            if res:
                break
        if count > 4 and not res:
            _logger.info("DB couldn't be cloned %s"%database_name)
            return False
    except Exception as e:
        _logger.info("%s cloned!!"%database_name)
        _logger.info("Error %s"%str(e))
        return False
    return True

def cloning_db(source_db,new_db):
   pg_host = 'localhost'
   pg_port = '9432'
   pg_user = 'odoo'
   pg_password = 'odoo'
   pg_database = "postgres"
   query = '''SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '%s';
       CREATE DATABASE %s WITH TEMPLATE %s OWNER %s;
       '''%(source_db,new_db,source_db,pg_user)
   with pgX:
       result = pgX.selectQuery(query)
   return result

@check_error
def create_new(client,database_name,user,passwd,admin_passwd): #send Odoo admin password. Using default (Admin) for now
    client.create_database(admin_passwd,database_name,user_password=passwd, login=user) #creating a new database, mentioning new db name, user name and password  
    _logger.info("%s created!!"%database_name)
    return True


def install_modules(client,modules = []):
    modules_missed = []
    for each in modules:
        try:
            client.install(each)
            time.sleep(1)
        except Exception as e:
            modules_missed.append(each)
            _logger.info("Module %s couldn't be installed. Erro:- %r"%(each,str(e)))
        else:
            _logger.info("Module %s installed"%each)
    return (False if len(modules_missed) else True, modules_missed)


def create_saas_client(operation = None, odoo_url=None, odoo_username = None, odoo_password = None, base_db=None, database_name=None,modules_list=[],admin_passwd = "admin"):

    response = {'modules_installation' : False, "modules_missed" : modules_list}
    if operation not in ['clone','create','install']:
        response['message'] = "Invalid Operation"
        return response
    _logger.info("Trying to connect DB")
    client = connect_db(odoo_url,base_db, odoo_username, odoo_password, flag = (True if operation != "clone" else False)) # base db for cloningelse it doesn't matter
    if not client:
        return response
    _logger.info("Connection Made %s"%client)
#     
    if operation == 'clone':
        _logger.info("Lets CLone DB!!")
        response['db_cloned'] = cloning(client, database_name, admin_passwd)  #admin_password  and database to be cloned into
        _logger.info("Lets CLone DB!! %r",response['db_cloned'])
    elif operation == 'create':
        response['db_create'] = create_new(client, database_name, odoo_username, odoo_password,admin_passwd) # new database name along with credentials

    if len(modules_list) and operation == 'install':
       client = connect_db(odoo_url,database_name, odoo_username, odoo_password, flag = False)
       if not client:
           response['modules_installation'] = False
           return response
       response['modules_installation'],response['modules_missed'] = install_modules(client, modules_list)
    return response
