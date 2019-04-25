##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class ResPartnerIdCategory(models.Model):

    _name = "l10n_ar_id_category"
    _description = "Identification Category"
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
        translate=True,
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
        """ Identification category can be searched by code or name
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
