from odoo import api, fields, models
from odoo.osv import expression


class TaxOffice(models.Model):
    _name = "l10n_tr.tax_office"
    _description = "Tax Office"

    name = fields.Char()
    code = fields.Char(size=6)
    partner_id = fields.Many2one(string="Contact", comodel_name="res.partner")
    state_id = fields.Many2one(comodel_name='res.country.state')
    type = fields.Selection(selection=[('office', 'Office'), ('bureau', 'Bureau')])

    @api.model
    def name_get(self):
        result = []
        for record in self:
            name = '%s %s' % (record.code, record.name)
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
