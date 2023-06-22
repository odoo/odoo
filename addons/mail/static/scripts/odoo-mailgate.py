#!/usr/bin/env python3
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This tool is sending mail to an Odoo instance (local or not). 

# Usage: 
#     send-mail.py <eml_file> 
# 					<-d <database>>
# 					[-u <url> default:"http://localhost:8069"] 
# 					[-U <user> default:"admin"] 
# 					[-p <password> default:"admin"]
# ]

# Commit odoo#ab70afb is removing the previously used route '/mail/receive'
# Now we use the xmlrpc function to log to the db and the odoo's method message_process of mail.thread,
# the first step on received emails.

# Working version: 8+

# import base64
import xmlrpc.client

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

parser = ArgumentParser(description='Send an email to Odoo databases',
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('eml_file', help='EML File to send')
parser.add_argument('-u', '--url', dest='url', default='http://localhost:8069', help='URL of the Odoo server')
parser.add_argument('-d', '--db', dest='db', required=True, help='Odoo database to send the email to')
parser.add_argument('-U', '--user', dest='username', default='admin', help='Login to connect with')
parser.add_argument('-p', '--password', dest='password', default='admin', help='Password to connect with')
args = parser.parse_args()

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(args.url))
uid = common.authenticate(args.db, args.username, args.password, {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(args.url))
with open(args.eml_file, 'rb') as f:
    message = f.read()
    #message = base64.b64encode(f.read()).decode()
models.execute_kw(args.db, uid, args.password, 'mail.thread', 'message_process', [False, message],)