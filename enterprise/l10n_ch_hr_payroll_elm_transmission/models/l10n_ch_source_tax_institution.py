# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from .hr_employee import CANTONS


class L10nCHSourceTaxInstitution(models.Model):
    _name = "l10n.ch.source.tax.institution"
    _description = "Source Tax Institution"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    canton = fields.Selection(selection=CANTONS, required=True)
    dpi_number = fields.Char(required=True, help="""
The DPI (Tax Source Identification) number is assigned by the ACI (Cantonal Tax Authority). 
For new declarations, request the DPI number from the ACI before submitting. 
Each entity or branch may have a separate DPI number or use a global DPI with separate company numbers for different declarations.""")
    company_number = fields.Char(help="""
If a company manages separate payrolls (e.g., for branches or subsidiaries), the ACI may assign individual company numbers under a global DPI. 
Use this field for any additional company number defined by the ACI.""")

    _sql_constraints = [
        ('ch_qst_canton_unique', 'unique(canton, company_id)', 'Only one Source-Tax Institution per Canton is possible.')
    ]
