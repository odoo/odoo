# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sst_registration_number = fields.Char(related='partner_id.sst_registration_number', readonly=False)
    ttx_registration_number = fields.Char(related='partner_id.ttx_registration_number', readonly=False)


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    sst_registration_number = fields.Char(related='company_id.sst_registration_number')
    ttx_registration_number = fields.Char(related='company_id.ttx_registration_number')
