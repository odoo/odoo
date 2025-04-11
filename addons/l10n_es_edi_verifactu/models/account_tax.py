from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_es_get_sujeto_tax_types(self):
        # TODO: other sujeto types; e.g. 'sujeto_agricultura'?
        return ('sujeto', 'sujeto_isp')

    def _l10n_es_edi_verifactu_get_tax_details_functions(self, simplified_invoice=False):
        def full_filter_invl_to_apply(line):
            return any(t != 'ignore' for t in line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type'))

        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)

        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id

            l10n_es_exempt_reason = tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False

            # We can map the tax type from FacturaE to Veri*Factu (since FacturaE is more detailed)
            if tax.l10n_es_edi_facturae_tax_type in ('01', '02', '03', '05'):
                verifactu_tax_type = tax.l10n_es_edi_facturae_tax_type
            else:
                verifactu_tax_type = '05'

            # Tax t with recargo and tax t without recargo are to be kept separate for the output
            # Note: We assume there is only a single (main tax, recargo tax) pair on a single base line
            with_recargo = False
            if tax.l10n_es_type in self.env['account.tax']._l10n_es_get_sujeto_tax_types():
                with_recargo = base_line['taxes'].filtered(lambda t: t.l10n_es_type == 'recargo')

            regimen_key = None
            VAT = verifactu_tax_type == '01'
            IGIC = verifactu_tax_type == '03'
            if VAT or IGIC:
                is_oss = oss_tag and oss_tag in tax_values['tax_repartition_line'].tag_ids
                export_exempts = l10n_es_exempt_reason == 'E2'
                if VAT and simplified_invoice:
                    regimen_key = '20'
                if VAT and with_recargo:
                    regimen_key = '18'
                elif VAT and is_oss:
                    regimen_key = '17'
                elif export_exempts:
                    regimen_key = '02'
                else:
                    regimen_key = '01'

            grouping_key = {
                'amount': tax.amount,
                'ClaveRegimen': regimen_key,
                'with_recargo': with_recargo,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_edi_verifactu_tax_type': verifactu_tax_type,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
            }
            return grouping_key

        def filter_to_apply(base_line, tax_values):
            return (tax_values['tax_repartition_line'].factor_percent > 0.0
                    and tax_values['tax_repartition_line'].tax_id.amount != -100.0
                    and tax_values['tax_repartition_line'].tax_id.l10n_es_type not in ('ignore', 'retencion'))

        return {
            'full_filter_invl_to_apply': full_filter_invl_to_apply,
            'grouping_key_generator': grouping_key_generator,
            'filter_to_apply': filter_to_apply,
        }
