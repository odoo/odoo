import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    def _default_encoding(self):
        return 'gs1-128' if self.env.context.get('is_gs1') else 'any'

    encoding = fields.Selection(
        selection_add=[('gs1-128', 'GS1-128')], default=_default_encoding,
        ondelete={'gs1-128': 'set default'})
    type = fields.Selection(
        selection_add=[
            ('quantity', 'Quantity'),
            ('location', 'Location'),
            ('location_dest', 'Destination location'),
            ('lot', 'Lot number'),
            ('package', 'Package'),
            ('use_date', 'Best before Date'),
            ('expiration_date', 'Expiration Date'),
            ('package_type', 'Package Type'),
            ('pack_date', 'Pack Date'),
        ], ondelete={
            'quantity': 'set default',
            'location': 'set default',
            'location_dest': 'set default',
            'lot': 'set default',
            'package': 'set default',
            'use_date': 'set default',
            'expiration_date': 'set default',
            'package_type': 'set default',
            'pack_date': 'set default',
        })
    is_gs1_nomenclature = fields.Boolean(related="barcode_nomenclature_id.is_gs1_nomenclature")
    gs1_content_type = fields.Selection([
        ('date', 'Date'),
        ('measure', 'Measure'),
        ('identifier', 'Numeric Identifier'),
        ('alpha', 'Alpha-Numeric Name'),
    ], string="GS1 Content Type",
        help="The GS1 content type defines what kind of data the rule will process the barcode as:\
        * Date: the barcode will be converted into a Odoo datetime;\
        * Measure: the barcode's value is related to a specific unit;\
        * Numeric Identifier: fixed length barcode following a specific encoding;\
        * Alpha-Numeric Name: variable length barcode.")
    gs1_decimal_usage = fields.Boolean('Decimal', help="If True, use the last digit of AI to determine where the first decimal is")
    associated_uom_id = fields.Many2one('uom.uom')

    @api.constrains('pattern')
    def _check_pattern(self):
        gs1_rules = self.filtered(lambda rule: rule.encoding == 'gs1-128')
        for rule in gs1_rules:
            try:
                re.compile(rule.pattern)
            except re.error as error:
                raise ValidationError(_("The rule pattern '%(rule)s' is not a valid Regex: %(error)s", rule=rule.name, error=error))
            groups = re.findall(r'\([^)]*\)', rule.pattern)
            if len(groups) != 2:
                raise ValidationError(_(
                    "The rule pattern \"%s\" is not valid, it needs two groups:"
                    "\n\t- A first one for the Application Identifier (usually 2 to 4 digits);"
                    "\n\t- A second one to catch the value.",
                    rule.name))

        super(BarcodeRule, (self - gs1_rules))._check_pattern()
