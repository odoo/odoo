from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import groupby

BARCODE_UNIQUENESS_MAP = {
    'stock.location': {'field': 'barcode', 'label': 'Location'},
    'product.product': {'field': 'barcode', 'label': 'Product', 'skip_model': 'product.uom'},
    'product.uom': {'field': 'barcode', 'label': 'Packaging', 'skip_model': 'product.product'},
    'stock.package.type': {'field': 'barcode', 'label': 'Package Type'},
    'stock.package': {'field': 'name', 'label': 'Package'},
    'stock.lot': {'field': 'name', 'label': 'Lot/Serial'},
    'stock.picking.type': {'field': 'barcode', 'label': 'Operation Type'},
}


class BarcodeUniquenessMixin(models.AbstractModel):
    _name = 'barcode.uniqueness.mixin'
    _description = "Barcode Uniqueness Mixin"
    _explanation = "Provides a reusable mechanism to ensure barcodes remain unique across different inventory objects, prevents assigning the same barcode to conflicting records."

    @api.constrains(lambda self: self._get_barcode_field_name())
    def _check_barcode_uniqueness(self):
        for company_id, barcodes_within_company in self._group_barcodes_by_company():
            if barcodes_within_company:
                self._check_duplicated_barcodes(barcodes_within_company, company_id)

    def _check_duplicated_barcodes(self, barcodes_within_company, company_id):
        for model_name, config in BARCODE_UNIQUENESS_MAP.items():
            if self._name in (model_name, config.get('skip_model')):
                continue
            domain = self.env[model_name]._get_duplicate_barcode_domain(config['field'], barcodes_within_company, company_id)
            if self.env[model_name].search_count(domain, limit=1):
                raise ValidationError(self.env._("The barcode is already assigned to a %(label)s.", label=config['label']))

    def _get_barcode_field_name(self):
        return [BARCODE_UNIQUENESS_MAP[self._name]['field']]

    def _get_duplicate_barcode_domain(self, field_name, barcodes, company_id):
        domain = Domain(field_name, 'in', barcodes)
        if company_id:
            domain = Domain.AND([domain, Domain('company_id', 'in', (False, company_id))])
        return domain

    def _group_barcodes_by_company(self):
        field_name = self._get_barcode_field_name()[0]
        return [
            (company_id, [r[field_name] for r in records if r[field_name]])
            for company_id, records in groupby(self, lambda r: r.company_id.id)
        ]
