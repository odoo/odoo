# ©  2008-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import _, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def action_post(self):
        # inainte de a face notele contabile trebuie sa verifica daca toate pozitiile din factura de achizitie
        # sunt legate de o comanda de aprovizonaoare

        purchase_invoices = self.filtered(lambda inv: inv.move_type == "in_invoice")
        if purchase_invoices:
            purchase_invoices.add_to_purchase()
            purchase_invoices.receipt_to_stock()
        return super(AccountInvoice, self).action_post()

    def add_to_purchase(self):
        """
            Verifica daca toate pozitiile din factura de achizitie se regasesc intr-o comanda de achizitie.
            sunt 2 variante: sa caut o comanda de aprovizonare
                                sau sa fac o comanda noua.
        """

        for invoice in self:
            if not invoice.invoice_date:
                raise UserError(_("Please enter invoice date"))
            # exista o comanda de achizitie legata de aceasta factura ?
            purchase_order = self.env["purchase.order"]
            for line in invoice.invoice_line_ids:
                purchase_order |= line.purchase_line_id.order_id

            # am gasit linii care nu sunt in comanda de achizitie
            lines_without_purchase = invoice.invoice_line_ids.filtered(lambda line: not line.purchase_line_id)
            # doar pentru prousele stocabile
            lines_without_purchase = lines_without_purchase.filtered(lambda line: line.product_id.type == "product")
            if lines_without_purchase:
                # trebuie sa verific daca sunt produse stocabile ?

                if len(purchase_order) != 1:

                    purchase_order = self.env["purchase.order"].create(
                        {
                            "partner_id": invoice.partner_id.id,
                            "date_order": invoice.invoice_date,
                            "partner_ref": invoice.ref,
                            "fiscal_position_id": invoice.fiscal_position_id.id,
                            "from_invoice_id": invoice.id,
                            "currency_id": invoice.currency_id.id,  # Preluare Moneda in comanda de achizitie
                            # "group_id": procurement_group.id
                        }
                    )

                for line in lines_without_purchase:
                    line_po = self.env["purchase.order.line"].create(
                        {
                            "order_id": purchase_order.id,
                            "date_planned": invoice.invoice_date,
                            "sequence": line.sequence,
                            "product_id": line.product_id.id,
                            "product_uom": line.product_uom_id.id,
                            "name": line.name,
                            "price_unit": line.price_unit,
                            "product_qty": line.quantity,
                            #  'discount': line.discount,  #
                            "taxes_id": [(6, 0, line.tax_ids.ids)],
                        }
                    )
                    line.write(
                        {
                            "purchase_line_id": line_po.id,
                            # 'purchase_id': purchase_order.id,
                        }
                    )
                if purchase_order.from_invoice_id:
                    # am eliminat contextul pentru ca se timitea move_type in  procurement.group
                    purchase_order.with_context({}).button_confirm()  # confirma comanda de achizitie
                    purchase_order.message_post_with_view(
                        "mail.message_origin_link",
                        values={"self": purchase_order, "origin": invoice},
                        subtype_id=self.env.ref("mail.mt_note").id,
                    )
                    link = (
                        "<a href=# data-oe-model=purchase.order data-oe-id="
                        + str(purchase_order.id)
                        + ">"
                        + purchase_order.name
                        + "</a>"
                    )
                    message = _("The purchase order %s was generated.") % link
                    invoice.message_post(body=message)

    def receipt_to_stock(self):
        purchase_orders = self.env["purchase.order"]
        for invoice in self:
            # trebuie sa determin care este cantitatea care trebuie sa fie receptionata
            for line in invoice.invoice_line_ids:
                purchase_orders |= line.purchase_line_id.order_id
        # doar pentru comenzile generate din factura se face receptia
        purchase_orders.filtered(lambda order: order.from_invoice_id).receipt_to_stock()
