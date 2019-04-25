# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.osv import expression


class L10nArIdentificationType(models.Model):

    _name = "l10n_ar.identification.type"
    _description = "Identification Type"
    _rec_name = "code"
    _order = "sequence"

    code = fields.Char(
        size=16,
        required=True,
        help="Abbreviation or acronym of this ID type. For example: 'PASS'",
    )
    name = fields.Char(
        string="ID name",
        required=True,
        help="Name of this ID type. For example: 'Passport'",
    )
    active = fields.Boolean(
        default=True,
    )
    sequence = fields.Integer(
        default=10,
        required=True,
    )
    afip_code = fields.Integer(
        required=True,
    )

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """ Identification type can be searched by code or name
        """
        args = args or []
        domain = []
        if name:
            domain = [
                '|',
                ('code', '=ilike', name + '%'),
                ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
