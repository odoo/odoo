# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.addons.l10n_vn_edi_viettel.models.sinvoice_service import SInvoiceService


class L10n_Vn_SinvoiceSymbol(models.Model):
    _inherit = 'l10n_vn.sinvoice.symbol'

    @api.model
    def _l10n_vn_edi_lookup_symbols(self, company):
        """Lookup available invoice symbols based on the company's tax code."""
        access_token, error = company._l10n_vn_edi_get_access_token()
        if error:
            return [], error
        with SInvoiceService(access_token=access_token, vat=company.vat, env=self.env) as sinvoice:
            return sinvoice.get_all_invoice_templates()

    def action_fetch_symbols(self):
        """Fetch symbols from the API and populate the list."""
        errors = []
        vn_companies = self.env.companies.filtered(lambda c: c.country_id.code == 'VN')

        if not vn_companies:
            raise UserError(_('Please select a Vietnamese company to fetch SInvoice symbol!'))

        existing_symbols = {
            (name, invoice_template_code, company_id): symbol
            for name, invoice_template_code, company_id, symbol in self.with_context(active_test=False)._read_group(
                domain=[('company_id', 'in', vn_companies.ids), ('usage', '=', 'invoice')],
                groupby=['name', 'invoice_template_code', 'company_id'],
                aggregates=['id:recordset'],
            )
        }

        seen_keys = set()
        symbols_to_create = []
        symbols_to_update = self.browse()

        for company in vn_companies:
            if not company.vat:
                errors.append(_('VAT number is missing on company %s.', company.display_name))
                continue

            templates, error = self._l10n_vn_edi_lookup_symbols(company)

            if error:
                errors.append(_('%(company)s: %(error)s', company=company.display_name, error=error))
                continue

            if not templates:
                errors.append(_('No symbols found for company %s. Please check your configuration and try again.', company.display_name))
                continue

            for symbol_data in templates:
                symbol_code = symbol_data.get('invoiceSeri')
                template_name = symbol_data.get('templateCode')
                key = (symbol_code, template_name, company)

                if key not in existing_symbols:
                    symbols_to_create.append({
                        'name': symbol_code,
                        'usage': 'invoice',
                        'invoice_template_code': template_name,
                        'company_id': company.id,
                    })
                else:
                    # A manually-created symbol may match a fetched SInvoice symbol.
                    # Mark it as fetched so the SInvoice link is protected going forward.
                    symbols_to_update |= existing_symbols[key]

                seen_keys.add(key)

        if symbols_to_create:
            symbols_to_update |= self.create(symbols_to_create)

        if symbols_to_update:
            symbols_to_update.write({
                'active': True,
                'is_fetched': True,
            })

        symbols_to_archive = [
            symbol
            for key, symbol in existing_symbols.items()
            if key not in seen_keys and symbol.is_fetched
        ]
        if symbols_to_archive:
            self.browse([s.id for s in symbols_to_archive]).write({'active': False})

        if errors:
            if len(vn_companies) == 1:
                raise UserError('\n'.join(msg.split(': ', 1)[-1] for msg in errors))
            else:
                raise UserError(_('Some companies encountered issues:\n\n%s', '\n'.join(errors)))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
