from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_tax_office_id = fields.Many2one(comodel_name='l10n_tr.tax_office', string='Tax Office')

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['l10n_tr_tax_office_id']

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_tr_tax_office_id']

    def _display_address_depends(self):
        # Not sure if it works properly
        return super()._display_address_depends() + [
            'l10n_tr_tax_office_id',
        ]

    def _prepare_display_address(self, without_company=False):
        address_format, args = super()._prepare_display_address(without_company=without_company)

        args.update({
            'l10n_tr_tax_office_name': self.l10n_tr_tax_office_id.name or '',
        })
        return address_format, args

    def _get_name(self):
        name = super()._get_name()
        if self._context.get('show_vat') and self.vat and self.l10n_tr_tax_office_id:
            name = "%s - %s" % (name, self.l10n_tr_tax_office_id.name)
        return name
