# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _name = 'report.project.task.user.fsm'
    _inherit = 'report.project.task.user'
    _description = "FSM Tasks Analysis"
    _auto = False

    partner_zip = fields.Char(string='ZIP', readonly=True)
    partner_city = fields.Char(string='City', readonly=True)
    partner_street = fields.Char(string='Street', readonly=True)
    partner_street2 = fields.Char(string='Street2', readonly=True)
    partner_country_id = fields.Many2one('res.country', string='Country', readonly=True)
    partner_state_id = fields.Many2one('res.country.state', string='Customer State', readonly=True)

    def _select(self):
        return super()._select() + """,
            rp.zip AS partner_zip,
            rp.city AS partner_city,
            rp.street AS partner_street,
            rp.street2 AS partner_street2,
            rp.country_id AS partner_country_id,
            rp.state_id AS partner_state_id
        """

    def _group_by(self):
        return super()._group_by() + """ ,
            rp.zip,
            rp.city,
            rp.street,
            rp.street2,
            rp.country_id,
            rp.state_id
        """

    def _from(self):
        return super()._from() + """
                INNER JOIN project_project pp
                    ON pp.id = t.project_id
                    AND pp.is_fsm = 'true'
                LEFT JOIN res_partner rp
                    ON rp.id = t.partner_id
        """
