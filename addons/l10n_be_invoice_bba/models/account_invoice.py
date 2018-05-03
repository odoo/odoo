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
"""


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_reference_type(self):
        res = super(AccountInvoice, self)._get_reference_type()
        res.append(('struct_comm', 'Structured Communication'))
        return res

    # This field's value will be used as label for `reference` field
    reference_type = fields.Selection('_get_reference_type', string='Payment Reference',
        required=True, readonly=True)

    @api.constrains('reference')
    def _check_communication(self):
        for inv in self:
            if inv.company_id.out_inv_comm_type == 'struct_comm' and not self.check_structcomm(inv.reference):
                raise ValidationError(_('Invalid Structured Communication !'))

    def check_structcomm(self, val):
        supported_chars = '0-9+*/ '
        pattern = re.compile('[^' + supported_chars + ']')
        if pattern.findall(val or ''):
            return False
        structcomm = re.sub('\D', '', val or '')
        if len(structcomm) == 12:
            base = int(structcomm[:10])
            mod = base % 97 or 97
            if mod == int(structcomm[-2:]):
                return True

    @api.onchange('company_id', 'partner_id', 'type')
    def _onchange_l10n_be_struct_comm(self):
        reference = False
        reference_type = self.company_id.out_inv_comm_type
        if self.type == 'out_invoice' and reference_type == 'struct_comm' and self.partner_id:
            reference = self.generate_structcomm(self.type, reference_type, self.company_id.id, self.partner_id.id)['value']['reference']
        self.reference_type = reference_type or 'none'
        self.reference = reference

    def generate_structcomm(self, type, reference_type, company_id, partner_id=None, reference=None):
        reference = reference or ''
        company = self.env['res.company'].browse(company_id)
        if type == 'out_invoice' and reference_type:
            algorithm = company.out_inv_comm_algorithm
            if reference_type == 'struct_comm':
                if algorithm == 'date':
                    if not self.check_structcomm(reference):
                        date = fields.Date.from_string(fields.Date.today())
                        doy = date.strftime('%j')
                        year = date.strftime('%Y')
                        seq = '001'
                        invoices = self.search([('type', '=', 'out_invoice'), ('reference_type', '=', 'struct_comm'),
                             ('reference', 'like', '+++%s/%s/%%' % (doy, year))], order='reference')
                        if invoices:
                            prev_seq = int(invoices[-1].reference[12:15])
                            if prev_seq < 999:
                                seq = '%03d' % (prev_seq + 1)
                            else:
                                raise UserError(_('The daily maximum of outgoing invoices with an automatically generated Structured Communications has been exceeded!'
                                                    '\nPlease create manually a unique Structured Communication.'))
                        structcomm = doy + year + seq
                        base = int(structcomm)
                        mod = base % 97 or 97
                        reference = '+++%s/%s/%s%02d+++' % (doy, year, seq, mod)
                elif algorithm == 'partner_ref':
                    if not self.check_structcomm(reference):
                        partner_ref = self.env['res.partner'].browse(partner_id).ref
                        partner_ref_nr = re.sub('\D', '', partner_ref or '')
                        if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
                            raise UserError(_('The Customer should have an Internal Reference with min 3 and max 7 digits'
                                                '\nfor the generation of Structured Communications!'))
                        else:
                            partner_ref_nr = partner_ref_nr.ljust(7, '0')
                            seq = '001'
                            invoices = self.search([('type', '=', 'out_invoice'), ('reference_type', '=', 'struct_comm'),
                                 ('reference', 'like', '+++%s/%s/%%' % (partner_ref_nr[:3], partner_ref_nr[3:]))], order='reference')
                            if invoices:
                                prev_seq = int(invoices[-1].reference[12:15])
                                if prev_seq < 999:
                                    seq = '%03d' % (prev_seq + 1)
                                else:
                                    raise UserError(_('The daily maximum of outgoing invoices with an automatically generated Structured Communications has been exceeded!'
                                                        '\nPlease create manually a unique Structured Communication.'))
                        structcomm = partner_ref_nr + seq
                        base = int(structcomm)
                        mod = base % 97 or 97
                        reference = '+++%s/%s/%s%02d+++' % (partner_ref_nr[:3], partner_ref_nr[3:], seq, mod)
                elif algorithm == 'random':
                    if not self.check_structcomm(reference):
                        base = random.randint(1, 9999999999)
                        structcomm = str(base).rjust(10, '0')
                        base = int(structcomm)
                        mod = base % 97 or 97
                        mod = str(mod).rjust(2, '0')
                        reference = '+++%s/%s/%s%s+++' % (structcomm[:3], structcomm[3:7], structcomm[7:], mod)
                else:
                    raise UserError(_("Unsupported Structured Communication Type Algorithm '%s' !"
                                        "\nPlease contact your Odoo support channel.") % algorithm)
        return {'value': {'reference': reference}}

    @api.model
    def create(self, vals):
        reference = vals.get('reference')
        company_id = vals.get('company_id') or self.default_get(['company_id'])['company_id']
        company = self.env['res.company'].browse(company_id)
        reference_type = company.out_inv_comm_type
        if reference_type == 'struct_comm':
            if reference:
                if self.check_structcomm(reference):
                    new_reference = re.sub('\D', '', reference)
                    reference = '+++' + new_reference[0:3] + '/' + new_reference[3:7] + '/' + new_reference[7:] + '+++'
                    same_ids = self.search([('type', '=', 'out_invoice'), ('reference_type', '=', 'struct_comm'), ('reference', '=', reference)])
                    if same_ids:
                        raise UserError(_('The Structured Communication has already been used!'
                                            '\nPlease create manually a unique Structured Communication.'))
                else:
                    raise ValidationError('Invalid Structured Communication !')
            else:
                reference = self.generate_structcomm(vals['type'], reference_type, company_id, vals['partner_id'])['value']['reference']
        vals.update({
            'reference_type': reference_type,
            'reference': reference,
        })
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, vals):
        for invoice in self:
            reference_type = invoice.company_id.out_inv_comm_type
            if 'reference_type' in vals:
                vals['reference_type'] = invoice.company_id.out_inv_comm_type
            if reference_type == 'struct_comm' and 'reference' in vals:
                if self.check_structcomm(vals['reference']):
                    reference = re.sub('\D', '', vals['reference'])
                    vals['reference'] = '+++' + reference[0:3] + '/' + reference[3:7] + '/' + reference[7:] + '+++'
                    same_ids = self.search([('id', '!=', invoice.id), ('type', '=', 'out_invoice'),
                         ('reference_type', '=', 'struct_comm'), ('reference', '=', vals['reference'])])
                    if same_ids:
                        raise UserError(_('The Structured Communication has already been used!'
                                            '\nPlease create manually a unique Structured Communication.'))
                else:
                    raise ValidationError('Invalid Structured Communication !')
        return super(AccountInvoice, self).write(vals)

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if self.type in ['out_invoice']:
            reference_type = self.reference_type or 'none'
            default['reference_type'] = reference_type
            if reference_type == 'struct_comm':
                default['reference'] = self.generate_structcomm(self.type, reference_type, self.company_id.id, self.partner_id.id)['value']['reference']
        return super(AccountInvoice, self).copy(default)
