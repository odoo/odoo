# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression

class EfakturProductCode(models.Model):
    _name = "l10n_id_efaktur_coretax.product.code"
    _description = "Product categorization according to E-Faktur"
    _rec_name = "code"

    code = fields.Char()
    description = fields.Text()

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f"{record.code} - {record.description}"))
        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []

        # Try to reverse the `name_get` structure
        parts = name.split(' - ')
        if len(parts) == 2:
            domain = [('code', operator, parts[0]), ('description', operator, parts[1])]
            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        if name and operator == 'ilike':
            domain = ['|',
                ('code', operator, name),
                ('description', operator, name),
            ]
            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super()._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
