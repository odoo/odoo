from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import groupby

BARCODE_UNIQUENESS_MAP = {
    'stock.location': {'label': 'Location'},
    'product.product': {'label': 'Product', 'skip_model': 'product.uom'},
    'product.uom': {'label': 'Packaging', 'skip_model': 'product.product'},
    'stock.package.type': {'label': 'Package Type'},
    'stock.picking.type': {'label': 'Operation Type'},
}


class BarcodeUniquenessMixin(models.AbstractModel):
    _name = 'barcode.uniqueness.mixin'
    _description = "Barcode Uniqueness Mixin"
    _explanation = "Provides a reusable mechanism to ensure barcodes remain unique across different inventory objects, prevents assigning the same barcode to conflicting records."

    barcode = fields.Char("Barcode", copy=False)

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        for company_id, barcodes_within_company in self._group_barcodes_by_company():
            if barcodes_within_company:
                self._check_duplicated_barcodes(barcodes_within_company, company_id)

    def _check_duplicated_barcodes(self, barcodes_within_company, company_id):
        domain = Domain("barcode", "in", barcodes_within_company)
        if company_id:
            domain = Domain.AND([domain, Domain('company_id', 'in', (False, company_id))])

        for model_name, config in BARCODE_UNIQUENESS_MAP.items():
            if self._name in (model_name, config.get('skip_model')):
                continue
            if self.env[model_name].search_count(domain, limit=1):
                raise ValidationError(self.env._("The barcode is already assigned to a %(label)s.", label=config['label']))

    def _group_barcodes_by_company(self):
        return [
            (company_id, [r.barcode for r in records if r.barcode])
            for company_id, records in groupby(self, lambda r: r.company_id.id)
        ]
