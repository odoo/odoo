# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang


class Witholding(models.Model):
    _name = "l10n_ec.witholding"

    company_id = fields.Many2one('res.company')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', _('Document Type'))
    witholding_move_id = fields.Many2one('account.move', _('Account Move'))
    invoice_id = fields.Many2one('account.move', _('Origin Document'))
    partner_id = fields.Many2one('res.partner')
    witholding_line_ids = fields.One2many('l10n_ec.witholding_line', 'witholding_id')
    currency_id = fields.Many2one('res.currency')
    amount_total= fields.Monetary('Total Amount', compute="_compute_amount")



class WitholdingLine(models.Model):
    _name = 'l10n_ec.witholding.lines'

    witholding_id = fields.Many2one('l10n_ec_witholding')
    tax_name = fields.Char(_('Tax'))
    currency_id = fields.Many2one('res.currency')
    base = fields.Monetary('Base')
    percent = fields.Float(_('Percent'))
    amount = fields.Monetary(_('Amount'))

