# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models

from odoo import api, SUPERUSER_ID


def _disable_pec_mail_post_init(cr, registry):
    ''' Pec mail cannot be used in conjunction with SdiCoop, so disable the Pec fetchmail servers.
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})

    env['fetchmail.server'].search([('l10n_it_is_pec', '=', True)]).l10n_it_is_pec = False
    env['res.company'].search([('l10n_it_mail_pec_server_id', '!=', None)]).l10n_it_mail_pec_server_id = None
