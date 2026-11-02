import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Product Return Tour
 *
 * Walks the user through the product return workflow:
 *  Draft → Confirm → Approve → Receive Return → Create Refund (or Reject)
 */
registry.category("web_tour.tours").add("od19_product_return_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's process a <b>Product Return</b> from customer to refund."))
        ),

        {
            trigger: navSection('Product Returns'),
            content: markup(_t("Open the <b>Product Returns</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [".o_dialog .btn-close"],
            trigger: ".o_dialog .btn-close",
            content: _t("Close the dialog to continue."),
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new product return."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the customer returning the product."),
            run: "click",
        },
        {
            // Scope to the `partner_id` field: a bare `.o-autocomplete--dropdown-item`
            // can match the stale/hidden dropdown of another mounted field.
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the customer from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='return_date'] .o_input",
            content: _t("Set the return date."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='sale_order_id'] input",
            content: markup(_t("Link the return to the original <b>Sales Order</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='invoice_id'] input",
            content: markup(_t("Link the return to the original <b>Invoice</b> (optional).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: _t("Select the returned product."),
            run: "click",
        },
        {
            // Scope to the `product_id` field: a bare `.o-autocomplete--dropdown-item`
            // can match the stale/hidden dropdown of another mounted field.
            trigger: ".o_field_widget[name='product_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the product from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='lot_id'] input",
            content: markup(_t("Set the <b>Lot/Serial Number</b> if tracked.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='quantity'] input",
            content: _t("Enter the returned quantity."),
            run: "edit 2",
        },
        {
            trigger: ".o_field_widget[name='reason'] .o_select_menu_toggler",
            content: _t("Enter the reason for the return."),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains('Defective')",
            content: _t("Pick the reason from the list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='refund_amount'] input",
            content: markup(_t("Set the <b>refund amount</b> to be credited back to the customer.")),
            run: "edit 10000",
        },
        ...stepUtils.saveForm(),

        // --- Product Return Workflow ---
        {
            trigger: "button[name='action_confirm']",
            content: markup(_t("Click <b>Confirm</b> to submit the return for approval.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_approve']",
            content: markup(_t("A manager clicks <b>Approve</b> to authorize the return.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_return']",
            content: markup(_t(
                "Click <b>Receive Return</b> to receive the goods back into stock. " +
                "This creates a return picking."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_refund'], .o_form_view",
            content: markup(_t(
                "Click <b>Create Refund</b> to generate a credit note for the customer. " +
                "Use <b>Reject</b> if the return is not approved."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_form_view, .o_list_renderer",
            content: markup(_t(
                "Product Return complete! Workflow: " +
                "<b>Draft → Confirm → Approve → Receive Return → Create Refund</b>. " +
                "The return can be rejected at any stage before refund."
            )),
            run: "click",
        },
    ],
});
