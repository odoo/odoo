# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    bacs_ddi_id = fields.Many2one(
        comodel_name='bacs.ddi',
        copy=False,
        help="Once this invoice has been paid with BACS Direct Debit, contains the DDI that allowed the payment.")
    bacs_has_usable_ddi = fields.Boolean(compute='_compute_bacs_has_usable_ddi', search='_search_bacs_has_usable_ddi')

    def _post(self, soft=True):
        # OVERRIDE
        # Register BACS Direct Debit payments on DDIs or trigger an error if no DDI is available.
        for pay in self.payment_id.filtered(lambda p: p.payment_method_code == 'bacs_dd'):
            usable_ddi = pay.get_usable_ddi()
            if not usable_ddi:
                raise UserError(_(
                    "Unable to post payment %(payment)r due to no usable DDI being available at date %(date)s for partner %(partner)r. Please create one before encoding a BACS Direct Debit payment.",
                    payment=pay.name,
                    date=pay.date,
                    partner=pay.partner_id.name,
                ))
            pay.bacs_ddi_id = usable_ddi

        return super()._post(soft)

    @api.model
    def _search_bacs_has_usable_ddi(self, operator, value):
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain_operator = 'in'
        else:
            domain_operator = 'not in'

        query = '''
        SELECT
            move.id
        FROM
            bacs_ddi ddi
        LEFT JOIN
            account_move move ON move.company_id = ddi.company_id AND
            move.commercial_partner_id = ddi.partner_id
        WHERE
            move.move_type IN ('out_invoice', 'in_refund') AND
            ddi.state NOT IN ('draft', 'revoked') AND
            ddi.start_date <= move.invoice_date
        '''

        self._cr.execute(query)

        return [('id', domain_operator, [x['id'] for x in self._cr.dictfetchall()])]

    @api.depends('company_id', 'commercial_partner_id', 'invoice_date')
    def _compute_bacs_has_usable_ddi(self):
        for rec in self:
            rec.bacs_has_usable_ddi = bool(rec._bacs_get_usable_ddi())

    def _bacs_get_usable_ddi(self):
        """ returns the first DDI found that can be used to pay this invoice,
        or none if there is no such DDI.
        """
        if self.move_type in ('out_invoice', 'in_refund'):
            return self.env['bacs.ddi']._bacs_get_usable_ddi(self.company_id.id, self.commercial_partner_id.id, self.invoice_date)
        else:
            return None


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        """
        Override of account move line Post-hook method for the reconciliation process.
        If the current account move line is linked to a payment that is associated with
        a BACS DDI, it retrieves the reconciled invoices related to the payment's move
        and assigns the BACS DDI to those invoices that do not have the same BACS DDI as the payment.
        """
        res = super().reconcile()

        for pay in self.payment_id:
            if pay.bacs_ddi_id:
                pay.move_id._get_reconciled_invoices().filtered(lambda m: m.bacs_ddi_id != pay.bacs_ddi_id).bacs_ddi_id = pay.bacs_ddi_id

        return res
