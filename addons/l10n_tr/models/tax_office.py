from odoo import api, fields, models


class TaxOffice(models.Model):
    _name = "l10n_tr.tax_office"
    _description = "Turkish Tax Office"
    _rec_names_search = ["name", "code"]

    name = fields.Char()
    code = fields.Char()
    type = fields.Selection(selection=[('office', 'Office'), ('bureau', 'Bureau')])

    @api.model
    def name_get(self):
        result = []
        for record in self:
            name = '%s %s' % (record.code, record.name)
            result.append((record.id, name))
        return result
