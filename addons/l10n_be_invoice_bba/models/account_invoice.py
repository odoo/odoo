# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

import random
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

"""
account.invoice object:
    - Add support for Belgian structured communication
    - Rename 'reference' field labels to 'Communication'
"""


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_reference_type(self):
        """Add BBA Structured Communication Type and change labels from 'reference' into 'communication' """
        res = super(AccountInvoice, self)._get_reference_type()
        res[[i for i, x in enumerate(res) if x[0] == 'none'][0]] = ('none', 'Free Communication')
        res.append(('bba', 'BBA Structured Communication'))
        return res

    reference_type = fields.Selection('_get_reference_type', string='Payment Reference',
        required=True, readonly=True)

    @api.constrains('reference', 'reference_type')
    def _check_communication(self):
        for inv in self:
            if inv.reference_type == 'bba' and not self.check_bbacomm(inv.reference):
                raise ValidationError('Invalid BBA Structured Communication !')

    def check_bbacomm(self, val):
        supported_chars = '0-9+*/ '
        pattern = re.compile('[^' + supported_chars + ']')
        if pattern.findall(val or ''):
            return False
        bbacomm = re.sub('\D', '', val or '')
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97
            if mod == int(bbacomm[-2:]):
                return True

    @api.onchange('partner_id', 'type')
    def _onchange_partner_id(self):
        result = super(AccountInvoice, self)._onchange_partner_id()
        reference = False
        reference_type = 'none'
        if self.partner_id:
            if (self.type == 'out_invoice'):
                reference_type = self.partner_id.out_inv_comm_type
                if reference_type:
                    reference = self.generate_bbacomm(self.type, reference_type, self.partner_id.id, '')['value']['reference']
        self.reference_type = reference_type or 'none'
        self.reference = reference
        return result

    @api.multi
    def generate_bbacomm(self, type, reference_type, partner_id, reference):
        reference = reference or ''
        algorithm = False
        if partner_id:
            algorithm = self.env['res.partner'].browse(partner_id).out_inv_comm_algorithm
        algorithm = algorithm or 'random'
        if (type == 'out_invoice'):
            if reference_type == 'bba':
                if algorithm == 'date':
                    if not self.check_bbacomm(reference):
                        date = fields.Date.from_string(fields.Date.today())
                        doy = date.strftime('%j')
                        year = date.strftime('%Y')
                        seq = '001'
                        invoices = self.search([('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                             ('reference', 'like', '+++%s/%s/%%' % (doy, year))], order='reference')
                        if invoices:
                            prev_seq = int(invoices[-1].reference[12:15])
                            if prev_seq < 999:
                                seq = '%03d' % (prev_seq + 1)
                            else:
                                raise UserError(_('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!'
                                                    '\nPlease create manually a unique BBA Structured Communication.'))
                        bbacomm = doy + year + seq
                        base = int(bbacomm)
                        mod = base % 97 or 97
                        reference = '+++%s/%s/%s%02d+++' % (doy, year, seq, mod)
                elif algorithm == 'partner_ref':
                    if not self.check_bbacomm(reference):
                        partner_ref = self.env['res.partner'].browse(partner_id).ref
                        partner_ref_nr = re.sub('\D', '', partner_ref or '')
                        if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
                            raise UserError(_('The Partner should have a 3-7 digit Reference Number for the generation of BBA Structured Communications!'
                                                '\nPlease correct the Partner record.'))
                        else:
                            partner_ref_nr = partner_ref_nr.ljust(7, '0')
                            seq = '001'
                            invoices = self.search([('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                                 ('reference', 'like', '+++%s/%s/%%' % (partner_ref_nr[:3], partner_ref_nr[3:]))], order='reference')
                            if invoices:
                                prev_seq = int(invoices[-1].reference[12:15])
                                if prev_seq < 999:
                                    seq = '%03d' % (prev_seq + 1)
                                else:
                                    raise UserError(_('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!'
                                                        '\nPlease create manually a unique BBA Structured Communication.'))
                        bbacomm = partner_ref_nr + seq
                        base = int(bbacomm)
                        mod = base % 97 or 97
                        reference = '+++%s/%s/%s%02d+++' % (partner_ref_nr[:3], partner_ref_nr[3:], seq, mod)
                elif algorithm == 'random':
                    if not self.check_bbacomm(reference):
                        base = random.randint(1, 9999999999)
                        bbacomm = str(base).rjust(10, '0')
                        base = int(bbacomm)
                        mod = base % 97 or 97
                        mod = str(mod).rjust(2, '0')
                        reference = '+++%s/%s/%s%s+++' % (bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
                else:
                    raise UserError(_("Unsupported Structured Communication Type Algorithm '%s' !"
                                        "\nPlease contact your Odoo support channel.") % algorithm)
        return {'value': {'reference': reference}}

    @api.model
    def create(self, vals):
        reference = vals.get('reference', False)
        reference_type = vals.get('reference_type', False)
        if vals.get('type') == 'out_invoice' and not reference_type:
            # fallback on default communication type for partner
            partner = self.env['res.partner'].browse(vals['partner_id'])
            reference_type = partner.out_inv_comm_type
            if reference_type == 'bba':
                reference = self.generate_bbacomm(vals['type'], reference_type, partner.id, '')['value']['reference']
            vals.update({
                'reference_type': reference_type or 'none',
                'reference': reference,
            })

        if reference_type == 'bba':
            if not reference:
                raise UserError(_('Empty BBA Structured Communication!'
                                    '\nPlease fill in a unique BBA Structured Communication.'))
            if self.check_bbacomm(reference):
                reference = re.sub('\D', '', reference)
                vals['reference'] = '+++' + reference[0:3] + '/' + reference[3:7] + '/' + reference[7:] + '+++'
                same_ids = self.search([('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'), ('reference', '=', vals['reference'])])
                if same_ids:
                    raise UserError(_('The BBA Structured Communication has already been used!'
                                        '\nPlease create manually a unique BBA Structured Communication.'))
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, vals):
        for invoice in self:
            if 'reference_type' in vals:
                reference_type = vals['reference_type']
            else:
                reference_type = invoice.reference_type or ''

            if reference_type == 'bba' and 'reference' in vals:
                if self.check_bbacomm(vals['reference']):
                    reference = re.sub('\D', '', vals['reference'])
                    vals['reference'] = '+++' + reference[0:3] + '/' + reference[3:7] + '/' + reference[7:] + '+++'
                    same_ids = self.search([('id', '!=', invoice.id), ('type', '=', 'out_invoice'),
                         ('reference_type', '=', 'bba'), ('reference', '=', vals['reference'])])
                    if same_ids:
                        raise UserError(_('The BBA Structured Communication has already been used!'
                                            '\nPlease create manually a unique BBA Structured Communication.'))
        return super(AccountInvoice, self).write(vals)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if self.type in ['out_invoice']:
            reference_type = self.reference_type or 'none'
            default['reference_type'] = reference_type
            if reference_type == 'bba':
                default['reference'] = self.generate_bbacomm(self.type, reference_type, self.partner_id.id, '')['value']['reference']
        return super(AccountInvoice, self).copy(default)
