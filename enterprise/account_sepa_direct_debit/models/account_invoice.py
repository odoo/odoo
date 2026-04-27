# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    sdd_mandate_id = fields.Many2one(related='origin_payment_id.sdd_mandate_id')
    sdd_has_usable_mandate = fields.Boolean(compute='_compute_sdd_has_usable_mandate', search='_search_sdd_has_usable_mandate')

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

        query = """
        SELECT
            move.id
        FROM
            sdd_mandate mandate
        LEFT JOIN
            account_move move ON move.company_id = mandate.company_id AND
            move.commercial_partner_id = mandate.partner_id
        WHERE
            move.move_type IN ('out_invoice', 'in_refund') AND
            mandate.state = 'active' AND
            mandate.start_date <= move.invoice_date AND
            (mandate.end_date IS NULL OR mandate.end_date > move.invoice_date)
        """

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
