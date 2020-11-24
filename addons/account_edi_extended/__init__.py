# -*- encoding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID


def account_edi_block_level(cr, registery):
    ''' The default value for blocking_level is 'error', but without this module,
    the behavior is the same as a blocking_level of 'warning' so we need to set
    all documents in error.
    '''

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['account.edi.document'].search([('error', '!=', False)]).write({'blocking_level': 'warning'})
