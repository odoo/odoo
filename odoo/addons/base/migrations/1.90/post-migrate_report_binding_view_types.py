# The FontAwesome 7 migration (4af1869b2c34) wrote
# binding_view_types = "list,kanban" onto 32 report actions that until then
# relied on the "list,form" default of ir.actions.actions. A report whose
# binding_view_types omits "form" is not offered in a form view's cog menu,
# because ir.ui.view spreads the toolbar over that field.
#
# dbd06602c369 removed the injected lines from the XML, but a field that a
# record no longer declares is never rewritten on update, so every database
# that went through the FA7 migration still carries the value. It stayed
# invisible while the forms had their own header Print buttons, and surfaced
# when d10ce9ba718b removed them: those documents lost every way to print
# from a form.
#
# "form" is appended rather than the literal default restored, so a database
# repaired by hand keeps what it carries and this migration is a no-op there.

from odoo import SUPERUSER_ID, api

REPORTS = (
    "account.account_invoices",
    "account.action_account_original_vendor_bill",
    "account.account_invoices_without_payment",
    "account.action_report_payment_receipt",
    "mrp.action_report_production_order",
    "mrp.action_report_bom_structure",
    "mrp.label_manufacture_template",
    "mrp.action_report_finished_product",
    "mrp.action_report_workorder",
    "purchase.action_report_purchase_order",
    "purchase.report_purchase_quotation",
    "sale.action_report_saleorder",
    "sale.action_report_pro_forma_invoice",
    "stock.return_label_report",
    "stock.action_report_picking",
    "stock.action_report_delivery",
    "stock.action_report_picking_packages",
    "stock.action_report_inventory",
    "stock.action_report_package_barcode",
    "stock.action_report_package_history_barcode",
    "stock.action_report_package_barcode_small",
    "stock.action_report_package_history_barcode_small",
    "stock.action_report_location_barcode",
    "stock.action_report_lot_label",
    "stock.action_report_picking_type_label",
    "stock.label_product_product",
    "stock.label_lot_template",
    "stock.label_package_template",
    "stock.label_package_history_template",
    "stock.label_packaging_barcode",
    "stock.label_picking_type",
    "stock.label_picking",
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xml_id in REPORTS:
        report = env.ref(xml_id, raise_if_not_found=False)
        if not report:
            continue
        view_types = [
            view_type.strip()
            for view_type in (report.binding_view_types or "").split(",")
            if view_type.strip()
        ]
        # An empty binding_view_types means every view type, so a record that
        # carries one is already reachable from its form.
        if not view_types or "form" in view_types:
            continue
        report.binding_view_types = ",".join([*view_types, "form"])
