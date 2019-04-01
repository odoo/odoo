# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID
from . import controllers
from . import models
from . import report
from . import wizard


def post_init(cr, registry):
    """Rewrite ICP's to force groups"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].init(force=True)


def neuter(cr,registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    neutralization_actions = [neuter_cron,
    neuter_mail,neuter_iap_services,
    ]
    for action in neutralization_actions:
        action(env)#call neutralization routine for the base module

def reverse_neuter(cr,registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    reverse_neutralization_actions = [reverse_neuter_cron,
    reverse_neuter_mail,reverse_neuter_iap_services,
    ]
    for action in reverse_neutralization_actions:
        action(env)#reverse the neutralization routine for the base module 

"""
Cron Routine
"""
def neuter_cron(env):
    to_neuters = env['ir.cron'].search([('active','=',True)])
    if to_neuters:
        to_neuters.write({'active':False,'has_been_neutered':True})

def reverse_neuter_cron(env):
    to_reverse_neuters = env['ir.cron'].with_context(active_test=False).search([('has_been_neutered','=',True)])
    if to_reverse_neuters:
        to_reverse_neuters.write({'active':True,'has_been_neutered':False})

"""
Mail routine
"""
def neuter_mail(env):
    to_neuters = env['ir.mail_server'].search([('active','=',True)])
    if to_neuters:
        to_neuters.write({'active':False,'has_been_neutered':True})

def reverse_neuter_mail(env):
    to_reverse_neuters = env['ir.mail_server'].with_context(active_test=False).search([('has_been_neutered','=',True)])
    if to_reverse_neuters:
        to_reverse_neuters.write({'active':True,'has_been_neutered':False})
"""
iap service routine
"""
def neuter_iap_services(env):
    """
    To ensure the neutralization, the key has to be insert even
    """
    ref_keys = ['snailmail.endpoint','reveal.endpoint',
    'iap.partner_autocomplete.endpoint','sms.endpoint',
    'iap.endpoint','ocn.ocn_push_notification',
    'odoo_ocn.project_id',
    ]
    for neuter in env['ir.config_parameter'].search([('key','in',ref_keys)]):
        key = neuter.key + "%s"
        if env['ir.config_parameter'].search([('key','=',key)]):
            neuter.write({'key':key %"-neuter"})

    ref_keys = [key for key in ref_keys if 'ocn' not in key]
    for key in ref_keys:
        if not env['ir.config_parameter'].search([('key','=',key)]):
            if key == 'iap.endpoint':
                env ['ir.config_parameter'].create({'key':key,'value':'https://iap-sandbox.odoo.com'})
            else:
                env ['ir.config_parameter'].create({'key':key,'value':"https://iap-services-test.odoo.com"})

def reverse_neuter_iap_services(env):
    ref_keys = ['snailmail.endpoint-neuter','reveal.endpoint-neuter',
    'iap.partner_autocomplete.endpoint-neuter','sms.endpoint-neuter',
    'iap.endpoint-neuter','ocn.ocn_push_notification-neuter',
    'odoo_ocn.project_id-neuter',
    ]
    to_delete_keys = [key.replace('-neuter','') for key in ref_keys]
    to_remove_neuter = env['ir.config_parameter'].search([
        ('key','in',to_delete_keys),'|',('value','=','https://iap-sandbox.odoo.com'),
        ('value','=','https://iap-services-test.odoo.com')])
    to_remove_neuter.unlink()
    for reverse in env['ir.config_parameter'].search([('key','in',ref_keys)]):
        key = reverse.key.replace('-neuter','')
        reverse.write({'key':key})
