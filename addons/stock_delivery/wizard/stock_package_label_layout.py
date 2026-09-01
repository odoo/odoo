from odoo import _, api, models


class PackageLabelLayout(models.TransientModel):
    _inherit = 'stock.package.label.layout'

    @api.model
    def _prepare_package_label_values(self, package):
        label = super()._prepare_package_label_values(package)
        weight = package.shipping_weight or package.weight
        if not weight:
            return label

        weight_name = _('Shipping Weight') if package.shipping_weight else _('Weight')
        label['weight_text'] = _('%(weight_name)s: %(weight)s %(uom)s', weight_name=weight_name, weight=weight, uom=package.weight_uom_name)
        if not package.valid_sscc:
            return label

        weight_str = str(int(weight / package.weight_uom_rounding))
        if len(weight_str) > 6:
            return label

        application_identifier = '310' if package.weight_is_kg else '320'
        decimals = len(str(package.weight_uom_rounding).split('.')[1])
        label['barcode_value'] += f'{application_identifier}{decimals}{weight_str.zfill(6)}'
        return label
