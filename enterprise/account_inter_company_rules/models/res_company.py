from odoo import api, fields, models, SUPERUSER_ID


class res_company(models.Model):
    _inherit = 'res.company'

    intercompany_generate_bills_refund = fields.Boolean(string="Generate Bills and Refunds")
    intercompany_document_state = fields.Selection(
        selection=[
            ('draft', "Create in draft"),
            ('posted', "Create and validate"),
        ],
        string="Automation",
        default='draft',
    )
    intercompany_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Purchase Journal",
        domain='[("type", "=", "purchase")]',
        compute='_compute_intercompany_purchase_journal_id', store=True, readonly=False,
    )
    intercompany_user_id = fields.Many2one(
        comodel_name='res.users',
        string="Create as",
        default=SUPERUSER_ID,
        domain=['|', ['active', '=', True], ['id', '=', SUPERUSER_ID]],
        help="Responsible user for creation of documents triggered by intercompany rules.",
    )

    @api.model
    def _find_company_from_partner(self, partner_id):
        if not partner_id:
            return False
        company = self.sudo().search([('partner_id', 'parent_of', partner_id)], limit=1)
        return company or False

    @api.depends('chart_template')
    def _compute_intercompany_purchase_journal_id(self):
        journals_by_company = dict(self.env['account.journal']._read_group(domain=[('type', '=', 'purchase')], groupby=['company_id'], aggregates=['id:recordset']))

        for company in self:
            if not company.intercompany_purchase_journal_id:
                company.intercompany_purchase_journal_id = journals_by_company.get(company, [False])[0]
