# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class CompleteChartsAccounts(models.TransientModel):
    _name = 'complete.chart.wizard'
    _description = 'Update chart of accounts from templates'

    @api.depends('company_id')
    def _compute_categories(self):
        imc_ids = self.env['ir.module.category'].sudo().search([])
        for wiz in self:
            wiz.allowed_categories_domain_ids = imc_ids.filtered(
                lambda c: c.xml_id in [
                    'base.module_category_localization',
                    'base.module_category_localization_account_charts'
                ]
            )


    company_id = fields.Many2one('res.company', 'Company', required=True, domain=[('chart_template_id', '!=', False)])
    chart_template_id = fields.Many2one(
        'account.chart.template', 'Chart Template',
        related='company_id.chart_template_id',required=True)
    update = fields.Boolean(default=False,
        help="If checked, additionally to loading all new records, also update existing ones.")
    allowed_categories_domain_ids = fields.Many2many('ir.module.category', compute=_compute_categories)
    module_id = fields.Many2one('ir.module.module', 'Module',
        help="If a module is selected, only records from that module are taken into account. "
             "All other records from other modules will be discarded and neither be loaded nor updated.")

    @api.multi
    def execute(self):
        if not self.env.user._is_admin():
            raise AccessError(_("Only administrators can change the settings"))
        ctx = dict({
            'chart_update': True,
            # Loading in update mode prevents noupdate records from updating
            # Template generated values are noupdate=True
            # Hence, switching off update mode will update those records, too.
            'load_in_update_mode': not self.update,
            'module_update': self.module_id.name if self.module_id else False
        }, **self.env.context)
        self.chart_template_id.with_context(ctx)._install_template(self.company_id)
