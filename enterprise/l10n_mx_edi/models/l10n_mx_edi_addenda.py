from lxml import etree
from lxml.etree import XMLSyntaxError

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_ADDENDA_ARCH = '''
<!-- Enter addenda definition here -->


'''


class Addenda(models.Model):
    _name = 'l10n_mx_edi.addenda'
    _description = 'Addenda for Mexican EDI'

    name = fields.Char(string='Name', required=True)
    arch = fields.Text(
        string='Architecture',
        required=True,
        default=DEFAULT_ADDENDA_ARCH,
    )

    @api.constrains('arch')
    def _validate_xml(self):
        for addenda in self:
            try:
                etree.fromstring(addenda.arch)
            except XMLSyntaxError as e:
                raise ValidationError(_('Invalid addenda definition:\n %s', e)) from e
