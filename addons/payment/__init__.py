# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID
from . import models
from . import controllers
from . import wizards


def neuter(cr,registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    to_neuters = env['payment.acquirer'].search([('environment','=','prod'),])
    if to_neuters:
        to_neuters.write({'environment':'test','has_been_neutered':True}) 

def reverse_neuter(cr,registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    to_reverse_neutering = env['payment.acquirer'].search([('has_been_neutered','=',True)])
    if to_reverse_neutering:
        to_reverse_neutering.write({'environment':'prod','has_been_neutered':False})