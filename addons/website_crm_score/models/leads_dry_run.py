from openerp import fields, models, api


class leads_dry_run(models.TransientModel):
    _name = "leads.dry.run"

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    section_id = fields.Many2one('crm.case.section', string='SaleTeam', required=True)
    user_id = fields.Many2one('res.users', string='Saleman')

    @api.model
    def assign_leads(self, ids=[]):
        # Allow to assign the result from a previous dry run.
        # Once the user agrees with the result shown by a dry run
        # It differs from launching the assignement process again,
        # because salemen would be selected at random  again
        dry_run_fields = ['lead_id',
                          'section_id',
                          'user_id',
                          ]
        all_dry_run = self.search_read(domain=[('user_id','!=',False)], fields=dry_run_fields)
        for dry_run in all_dry_run:
            lead_record = self.env['crm.lead'].browse(dry_run['lead_id'][0])
            values = {
                'section_id': dry_run['section_id'][0],
                'user_id': dry_run['user_id'][0],
                'assign_date': fields.Datetime.now()
            }
            lead_record.write(values)
            lead_record.convert_opportunity(partner_id=None)

        # Avoid to re-assign the same leads for nothing
        self._cr.execute("""
                TRUNCATE TABLE leads_dry_run;
        """)
