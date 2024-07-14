# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, values):
        company = super().create(values)
        company._create_helpdesk_team()
        return company

    def _create_helpdesk_team(self):
        results = []
        stage_ids = []
        for xml_id in ['stage_new', 'stage_in_progress', 'stage_solved', 'stage_cancelled', 'stage_on_hold']:
            record = self.env.ref(f'helpdesk.{xml_id}', False)
            if record:
                stage_ids.append(record.id)
        team_name = _('Customer Care')
        for company in self:
            company = company.with_company(company)
            results += [{
                'name': team_name,
                'company_id': company.id,
                'use_sla': False,
                'stage_ids': [Command.set(stage_ids)],
                'alias_name': "%s-%s" % (team_name, company.name),
            }]
        # use sudo as the user could have the right to create a company
        # but not to create a team for other company.
        return self.env['helpdesk.team'].sudo().create(results)
