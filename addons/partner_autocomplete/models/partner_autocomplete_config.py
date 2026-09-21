from odoo import fields, models


class PartnerAutocompleteConfig(models.Model):
    _name = "partner_autocomplete.config"
    _description = "A company's partner autocomplete configuration"
    _inherit = ["mixin.company.config"]

    iap_enrich_auto_done = fields.Boolean(string="Enrich Done")
