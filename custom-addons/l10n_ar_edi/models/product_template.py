from odoo import fields, models, _
from odoo.exceptions import UserError
import re


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    l10n_ar_ncm_code = fields.Char('NCM Code', copy=False, help='Code according to the Common Nomenclator of MERCOSUR')

    def _check_l10n_ar_ncm_code(self):
        self.ensure_one()
        if self.l10n_ar_ncm_code and not re.match(r'^[0-9\.]+$', self.l10n_ar_ncm_code):
            raise UserError(_(
                'it seems like the product "%s" has no valid NCM Code.\n\nPlease set a valid NCM code to continue.'
                ' You can go to AFIP page and review the list of available NCM codes', self.display_name))
