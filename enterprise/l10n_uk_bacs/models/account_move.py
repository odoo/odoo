# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    bacs_ddi_id = fields.Many2one('bacs.ddi', compute='_compute_bacs_ddi_id')
    bacs_has_usable_ddi = fields.Boolean(compute='_compute_bacs_has_usable_ddi', search='_search_bacs_has_usable_ddi')

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

    @api.depends('origin_payment_id.bacs_ddi_id', 'matched_payment_ids.bacs_ddi_id')
    def _compute_bacs_ddi_id(self):
        for move in self:
            move.bacs_ddi_id = move.origin_payment_id.bacs_ddi_id or move.matched_payment_ids.bacs_ddi_id[:1]

    def _bacs_get_usable_ddi(self):
        """ returns the first DDI found that can be used to pay this invoice,
        or none if there is no such DDI.
        """
        if self.move_type in ('out_invoice', 'in_refund'):
            return self.env['bacs.ddi']._bacs_get_usable_ddi(self.company_id.id, self.commercial_partner_id.id, self.invoice_date)
        else:
            return None
