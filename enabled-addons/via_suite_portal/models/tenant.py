# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ViaSuiteTenant(models.Model):
    _name = 'via_suite.tenant'
    _description = 'ViaSuite Tenant'
    _order = 'name'

    name = fields.Char(string='Tenant Name', required=True)
    subdomain = fields.Char(string='Subdomain', required=True, help="Short name used in the URL: [subdomain].viafronteira.app")
    active = fields.Boolean(default=True)
    description = fields.Text()
    
    _sql_subdomain_unique = models.Constraint(
        'UNIQUE(subdomain)',
        'The subdomain must be unique!'
    )

    @api.depends('subdomain')
    def _compute_full_url(self):
        import os
        base_domain = os.getenv('VIA_SUITE_GLOBAL_DOMAIN', 'viafronteira.app')
        for tenant in self:
            tenant.full_url = f"https://{tenant.subdomain}.{base_domain}"

    full_url = fields.Char(string='Full URL', compute='_compute_full_url')

    def action_go_to_tenant(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.full_url,
            'target': 'new',
        }
