# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    sdd_mandate_scheme = fields.Selection(related='sdd_mandate_id.sdd_scheme', readonly=True)
    sdd_mandate_id = fields.Many2one(
        comodel_name='sdd.mandate',
        copy=False,
        help="Once this invoice has been paid with Direct Debit, contains the mandate that allowed the payment.")
    sdd_has_usable_mandate = fields.Boolean(compute='_compute_sdd_has_usable_mandate', search='_search_sdd_has_usable_mandate')

    def _post(self, soft=True):
        # OVERRIDE
        # Register SDD payments on mandates or trigger an error if no mandate is available.
        for pay in self.payment_id.filtered(lambda p: p.payment_method_code in p.payment_method_id._get_sdd_payment_method_code()):
            usable_mandate = pay.get_usable_mandate()
            if not usable_mandate:
                raise UserError(_(
                    "Unable to post payment %(payment)r due to no usable mandate being available at date %(date)s for partner %(partner)r. Please create one before encoding a SEPA Direct Debit payment.",
                    payment=pay.name,
                    date=pay.date,
                    partner=pay.partner_id.name,
                ))
            pay.sdd_mandate_id = usable_mandate

        return super()._post(soft)

    @api.model
    def _search_sdd_has_usable_mandate(self, operator, value):
        """ Returns invoice ids for which a mandate exist that can be used to be paid,
            as domain : [('id', 'in', '[4,24,89]')]
            SQL is used to minimise footprint and is the same as :
            res = self.search([]).filtered(lambda rec: rec.sdd_has_usable_mandate is True and not rec.is_outbound())
            return [('id', domain_operator, [x['id'] for x in res])]
        """

        if (operator == '=' and value) or (operator == '!=' and not value):
            domain_operator = 'in'
        else:
            domain_operator = 'not in'

        query = '''
        SELECT
            move.id
        FROM
            sdd_mandate mandate
        LEFT JOIN
            account_move move ON move.company_id = mandate.company_id AND
            move.commercial_partner_id = mandate.partner_id
        WHERE
            move.move_type IN ('out_invoice', 'in_refund') AND
            mandate.state NOT IN ('draft', 'revoked') AND
            mandate.start_date <= move.invoice_date AND
            (mandate.end_date IS NULL OR mandate.end_date > move.invoice_date)
        '''

        self._cr.execute(query)

        return [('id', domain_operator, [x['id'] for x in self._cr.dictfetchall()])]

    @api.depends('company_id', 'commercial_partner_id', 'invoice_date')
    def _compute_sdd_has_usable_mandate(self):
        for rec in self:
            rec.sdd_has_usable_mandate = bool(rec._sdd_get_usable_mandate())

    def _sdd_get_usable_mandate(self):
        """ returns the first mandate found that can be used to pay this invoice,
        or none if there is no such mandate.
        """
        if self.move_type in ('out_invoice', 'in_refund'):
            return self.env['sdd.mandate']._sdd_get_usable_mandate(self.company_id.id, self.commercial_partner_id.id, self.invoice_date)
        else:
            return None

    def _track_subtype(self, init_values):
        # OVERRIDE to log a different message when an invoice is paid using SDD.
        self.ensure_one()
        if 'state' in init_values and self.state in ('in_payment', 'paid') and self.move_type == 'out_invoice' and self.sdd_mandate_id:
            return self.env.ref('account_sepa_direct_debit.sdd_mt_invoice_paid_with_mandate')
        return super(AccountMove, self)._track_subtype(init_values)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _reconcile_post_hook(self, data):
        # EXTENDS 'account'
        super()._reconcile_post_hook(data)

        for pay in self.payment_id:
            if pay.sdd_mandate_id:
                pay.move_id._get_reconciled_invoices().filtered(lambda m: m.sdd_mandate_id != pay.sdd_mandate_id).sdd_mandate_id = pay.sdd_mandate_id

                if pay.sdd_mandate_id.one_off:
                    pay.sdd_mandate_id.action_close_mandate()
