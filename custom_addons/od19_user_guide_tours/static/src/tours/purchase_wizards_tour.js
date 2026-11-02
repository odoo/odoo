import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Wizards Tour
 *
 * Walks the user through:
 *  1. Trade Discount wizard on a draft purchase order
 *  2. Creating a vendor bill from a confirmed purchase order
 *  3. Extra reference fields (Your Ref) on purchase orders
 */
registry.category("web_tour.tours").add("od19_purchase_wizards_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("Let's learn the <b>Purchase Wizards</b>: trade discount and vendor bill creation."))
        ),

        {
            trigger: navSection('Orders'),
            content: markup(_t("Open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Purchase Orders'),
            content: markup(_t("Open <b>Purchase Orders</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new purchase order."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the vendor."),
            run: "click",
        },
        {
            // Scope to the `partner_id` field: a bare `.o-autocomplete--dropdown-item`
            // can match the stale/hidden dropdown of another mounted field.
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the vendor from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_your_ref'] input",
            content: markup(_t(
                "Enter <b>Your Reference</b> - the vendor's document number for this order."
            )),
            run: "edit PO-2026-001",
        },
        {
            trigger: "button[name='action_od19_trade_discount']",
            content: markup(_t(
                "On a <b>draft</b> order, click <b>Trade Discount</b> to apply a percentage or amount " +
                "discount across the order lines in one step."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_dialog .btn-close",
            content: _t("Close the Trade Discount wizard to return to the order."),
            run: "click",
        },
        {
            trigger: ".o_list_renderer, .o_form_view",
            content: markup(_t(
                "Enter the order lines and <b>Confirm</b> the order. Once the order is confirmed, " +
                "the <b>Create Vendor Bill</b> button becomes available."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer, .o_form_view",
            content: markup(_t(
                "Click <b>Create Vendor Bill</b> to generate the vendor bill from the received " +
                "quantities. The bill is created as a <b>draft</b> so accounting can verify the " +
                "invoice number and date before posting."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Purchase Wizards complete! <b>Trade Discount</b> speeds up order pricing and " +
                "<b>Create Vendor Bill</b> turns a confirmed order into a draft vendor bill."
            )),
            run: "click",
        },
    ],
});
