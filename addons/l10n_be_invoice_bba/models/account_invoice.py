# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

import random
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

"""
account.invoice object: add support for Belgian structured communication
"""


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def generate_bbacomm(self):
        self.ensure_one()
        algorithm = self.company_id.l10n_be_structured_comm
        if algorithm == 'date':
            date = fields.Date.from_string(fields.Date.today())
            doy = date.strftime('%j')
            year = date.strftime('%Y')
            seq = '001'
            invoices = self.search([('type', '=', 'out_invoice'),
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
            partner_ref = self.partner_id.ref
            print(partner_ref)
            partner_ref_nr = re.sub('\D', '', partner_ref or '')
            if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
                raise UserError(_('The Customer should have an Internal Reference with min 3 and max 7 digits'
                                    '\nfor the generation of BBA Structured Communications!'))
            else:
                partner_ref_nr = partner_ref_nr.ljust(7, '0')
                seq = '001'
                invoices = self.search([('type', '=', 'out_invoice'),
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
            base = random.randint(1, 9999999999)
            bbacomm = str(base).rjust(10, '0')
            base = int(bbacomm)
            mod = base % 97 or 97
            mod = str(mod).rjust(2, '0')
            reference = '+++%s/%s/%s%s+++' % (bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
        else:
            raise UserError(_("Unsupported Structured Communication Type Algorithm '%s' !"
                                "\nPlease contact your Odoo support channel.") % algorithm)
        return reference

    @api.multi
    def _get_computed_reference(self):
        self.ensure_one()
        if self.company_id.invoice_reference_type == 'structured':
            return self.generate_bbacomm()
        return super(AccountInvoice, self)._get_computed_reference()
