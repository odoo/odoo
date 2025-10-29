from odoo import Command, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(model='account.move', demo=True)
    def _l10n_sa_edi_onboard_sa_sale_demo(self, template_code):
        if template_code == "sa":
            self._l10n_sa_edi_update_res_partner_demo()
            sa_sale_journal = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)
            sa_sale_journal._l10n_sa_api_onboard_journal('123345')

            demo_invoices = (
                self.ref('demo_sa_invoice_1', raise_if_not_found=False)
                + self.ref('demo_sa_invoice_2', raise_if_not_found=False)
                + self.ref('demo_sa_invoice_3', raise_if_not_found=False)
                + self.ref('demo_sa_invoice_4', raise_if_not_found=False)
            )
            for invoice in demo_invoices:
                invoice.update({
                    "edi_document_ids": [
                        Command.clear(),
                        *[
                            Command.create({
                                "edi_format_id": edi_format.id,
                                "state": "to_send",
                            })
                            for edi_format in invoice.journal_id.edi_format_ids
                        ],
                    ],
                })
                invoice.button_process_edi_web_services()

    def _l10n_sa_edi_update_res_partner_demo(self):
        demo_partner_updates = {
            'base.partner_demo_company_sa': {
                'l10n_sa_edi_building_number': '7450',
                'l10n_sa_edi_plot_identification': '3495',
                'l10n_sa_edi_additional_identification_scheme': 'CRN',
                'l10n_sa_edi_additional_identification_number': '1008434875',
            },
            'l10n_sa.partner_demo_customer_company_1_sa': {
                'l10n_sa_edi_building_number': '8421',
                'l10n_sa_edi_plot_identification': '4519',
                'l10n_sa_edi_additional_identification_scheme': 'CRN',
                'l10n_sa_edi_additional_identification_number': '1017654321',
            },
            'l10n_sa.partner_demo_customer_company_2_sa': {
                'l10n_sa_edi_building_number': '7734',
                'l10n_sa_edi_plot_identification': '2893',
                'l10n_sa_edi_additional_identification_scheme': 'CRN',
                'l10n_sa_edi_additional_identification_number': '1014567890',
            },
            'l10n_sa.partner_demo_vendor_1_sa': {
                'l10n_sa_edi_building_number': '3885',
                'l10n_sa_edi_plot_identification': '1331',
                'l10n_sa_edi_additional_identification_scheme': 'CRN',
                'l10n_sa_edi_additional_identification_number': '1003672815',
            },
            'l10n_sa.partner_demo_vendor_2_sa': {
                'l10n_sa_edi_building_number': '6529',
                'l10n_sa_edi_plot_identification': '3478',
                'l10n_sa_edi_additional_identification_scheme': 'CRN',
                'l10n_sa_edi_additional_identification_number': '1012349812',
            },
        }

        for xml_id, values in demo_partner_updates.items():
            if partner := self.with_company(self.env.company.id).ref(xml_id, raise_if_not_found=False):
                partner.write(values)
