# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    l10n_nl_sbr = fields.Many2one('l10n_nl.sbr', string='SBR Code',
                                  help='The corresponding SBR code of the account.')


class AccountAccounte(models.Model):
    _inherit = 'account.account'

    l10n_nl_sbr = fields.Many2one('l10n_nl.sbr', string='SBR Code',
                                  help='The corresponding SBR code of the account.')
