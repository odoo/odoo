# -*- coding: utf-8 -*-
from openerp import fields, models, api


class leads_dry_run(models.TransientModel):
    _name = "leads.dry.run"

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    team_id = fields.Many2one('crm.team', string='SaleTeam', required=True, oldname='section_id')
    user_id = fields.Many2one('res.users', string='Saleman')

    @api.model
    def assign_leads(self, ids=[]):
        # Allow to assign the result from a previous dry run.
        # Once the user agrees with the result shown by a dry run
        # It differs from launching the assignement process again,
        # because salemen would be selected at random again
        all_dry_run = self.search([('user_id', '!=', False)])
        for dry_run in all_dry_run:
            lead_record = dry_run.lead_id
            values = {
                'team_id': dry_run.team_id.id,
                'user_id': dry_run.user_id.id,
                'assign_date': fields.Datetime.now()
            }
            lead_record.write(values)
            lead_record.convert_opportunity(partner_id=None)

        # Avoid to re-assign the same leads for nothing
        self._cr.execute("""
                TRUNCATE TABLE leads_dry_run;
        """)
