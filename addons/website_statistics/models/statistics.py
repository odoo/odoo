# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo import api, fields, models, tools


class Statistics(models.Model):
    _name = "statistics.statistics"
    _description = "Keep track of a partner actions."

    res_model_id = fields.Many2one('ir.model', 'Related Document Model', index=True, ondelete='cascade', help='Model of the followed resource')
    res_model = fields.Char(string='Document Model', related='res_model_id.model', store=True, index=True, readonly=True)
    res_id = fields.Integer(string='Document', required=True, help="Identifier of the tracked object", index=True)

    partner_id = fields.Many2one('res.partner', index=True, ondelete='cascade', required=True)

    view_date = fields.Datetime('Last time seen', default=fields.Datetime.now(), index=True)

    _sql_constraints = [
        ('unique_document_per_partner', 'UNIQUE (partner_id, res_model_id, res_id)', 'Triple partner_id/res_model_id/res_id must be unique.'),
    ]

    @api.model
    def update_statistics_view(self, values, test=False):
        # returns True if the statistics is update, the record if it is created, False otherwise
        res_model_id = values.get('res_model_id')
        res_id = values.get('res_id')
        if not res_id or not res_model_id:
            return False

        partner_id = values.get('partner_id')

        view_date = values.get('view_date')
        if not view_date:
            view_date = fields.Datetime.now()

        with self.pool.cursor() as pv_cr:
            if test:
                pv_cr = self._cr
            pv_cr.execute(
                '''UPDATE statistics_statistics SET view_date=%s WHERE res_model_id=%s AND res_id=%s AND partner_id=%s RETURNING id;''',
                (view_date, res_model_id, res_id, partner_id)
            )
            fetch = pv_cr.fetchone()
            if fetch:
                return True
            else:
                # update failed
                try:
                    return self.create(values)
                except IntegrityError:
                    return False
