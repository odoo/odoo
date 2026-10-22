# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_ph.tests.common import TestPhCommon


class TestPhInvoiceCommon(TestPhCommon):

    def _create_wizard(self, invoice, **vals):
        """Open the wizard on ``invoice`` like the button does, then apply ``vals``."""
        action = invoice.action_open_discount_privilege_wizard()
        wizard = self.env["l10n_ph.discount.privilege.wizard"].browse(action["res_id"])
        if vals:
            wizard.write(vals)
        return wizard

    def _apply_privilege(self, invoice, **vals):
        """Open the wizard, apply ``vals`` and confirm; returns the wizard."""
        wizard = self._create_wizard(invoice, **vals)
        wizard.action_confirm()
        return wizard

    @classmethod
    def _create_invoice_with_lines(cls, *lines, **kwargs):
        """Create an invoice from ``(name, product, price_unit[, line_vals])`` specs."""
        invoice_line_ids = []
        for line in lines:
            name, product, price_unit = line[:3]
            line_values = line[3] if len(line) > 3 else {}
            invoice_line_ids.append(
                cls._prepare_invoice_line(
                    name=name,
                    product_id=product,
                    price_unit=price_unit,
                    **line_values,
                ),
            )
        return cls._create_invoice(invoice_line_ids=invoice_line_ids, **kwargs)
