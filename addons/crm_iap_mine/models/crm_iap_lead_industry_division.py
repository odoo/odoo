# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmIapLeadIndustryDivision(models.Model):
    """ Industry Divisions, further classified in Major Groups """
    _name = 'crm.iap.lead.industry.division'
    _description = "CRM IAP Lead Industry Division"

    name = fields.Char(string="Division Name", required=True, translate=True)
    division = fields.Char(string="Division Code", required=True, help="Division code as per SIC indicating the higher-level industry classification.")

    _name_uniq = models.Constraint(
        'unique (name)',
        "Industry Division already exists!",
    )
