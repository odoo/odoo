# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api



class TenantCodeConfiguration(models.Model):
    _name = 'tenant.code.configuration'
    _description = 'Tenant Code Configuration.'

    name = fields.Char(string='Tenant Code')
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.model
    def create(self, vals):
        """Override the create method to update partner with the tenant code."""
        record = super(TenantCodeConfiguration, self).create(vals)
        if record.partner_id:
            record.partner_id.tenant_code_id = record.id  # Update the tenant_code_id field in partner
        return record

    def write(self, vals):
        """Override the write method to update partner with the tenant code if modified."""
        res = super(TenantCodeConfiguration, self).write(vals)
        if 'partner_id' in vals or 'name' in vals:
            for record in self:
                if record.partner_id:
                    record.partner_id.tenant_code_id = record.id  # Ensure the partner is updated with the new tenant code
        return res

