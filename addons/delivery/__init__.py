# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID
from . import models
from . import wizard


def neuter(cr,registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    to_neuters = env['delivery.carrier'].search([('prod_environment','=',True),])
    if to_neuters:
        to_neuters.write({'prod_environment':False,'has_been_neutered':True}) 

def reverse_neuter(cr,registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    to_reverse_neutering = env['delivery.carrier'].search([('has_been_neutered','=',True)])
    if to_reverse_neutering:
        to_reverse_neutering.write({'prod_environment':True,'has_been_neutered':False})
