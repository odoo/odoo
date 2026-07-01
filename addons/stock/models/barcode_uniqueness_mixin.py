from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import groupby

BARCODE_CHECK_MAP = {
    'stock.location': {'field': 'barcode', 'label': 'Location'},
    'product.product': {'field': 'barcode', 'label': 'Product'},
    'product.uom': {'field': 'barcode', 'label': 'Packaging'},
    'stock.package.type': {'field': 'barcode', 'label': 'Package Type'},
    'stock.package': {'field': 'name', 'label': 'Package'},
    'stock.lot': {'field': 'name', 'label': 'Lot/Serial'},
    'stock.picking.type': {'field': 'barcode', 'label': 'operation type'},
}


class BarcodeUniquenessMixin(models.AbstractModel):
    _name = 'barcode.uniqueness.mixin'
    _description = 'Barcode Uniqueness Mixin'

    def _get_barcode_fname(self):
        """Return the name of the field containing the barcode to check for uniqueness.
        """
        return [BARCODE_CHECK_MAP[self._name]['field']]

    def _get_models_to_skip(self):
        """Return the list of models to skip when checking for duplicate barcodes.
        """
        return []

    def _group_barcodes_by_company(self):
        field_name = self._get_barcode_fname()[0]
        return [
            (company_id, [r[field_name] for r in records if r[field_name]])
            for company_id, records in groupby(self, lambda r: r.company_id.id)
        ]

    def _get_duplicate_barcode_domain(self, field_name, barcodes, company_id):
        """Return the domain to check for duplicate barcodes.
        """
        domain = [(field_name, 'in', barcodes)]
        if company_id:
            domain.append(('company_id', 'in', (False, company_id)))
        return domain

    def _check_duplicated_barcodes(self, barcodes_within_company, company_id):
        """Ensure barcodes are not already used in other models.

        :param list barcodes_within_company: Barcodes to check for duplicates within the same company.
        :param int|bool company_id: Company ID to check the barcodes against.
        :raises ValidationError: If a duplicate is found.
        """
        models_to_skip = self._get_models_to_skip()
        for model_name, config in BARCODE_CHECK_MAP.items():
            if self._name == model_name or model_name in models_to_skip:
                continue
            domain = self.env[model_name]._get_duplicate_barcode_domain(config['field'], barcodes_within_company, company_id)
            if self.env[model_name].search_count(domain, limit=1):
                raise ValidationError(self.env._("The barcode is already assigned to a %s.", config['label']))

    @api.constrains(lambda self: self._get_barcode_fname())
    def _check_barcode_uniqueness(self):
        for company_id, barcodes_within_company in self._group_barcodes_by_company():
            self._check_duplicated_barcodes(barcodes_within_company, company_id)
