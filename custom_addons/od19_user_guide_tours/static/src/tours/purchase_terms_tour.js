import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Terms Tour
 *
 * Walks the user through:
 *  1. Creating reusable purchase term templates
 *  2. Applying terms on a purchase order (Terms tab)
 */
registry.category("web_tour.tours").add("od19_purchase_terms_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("Let's set up reusable <b>Purchase Term Templates</b> and apply them on orders."))
        ),

        // --- Term templates ---
        {
            trigger: navSection('Configuration'),
            content: markup(_t("Open the Purchase <b>Configuration</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Purchase Term Templates'),
            content: markup(_t("Open <b>Purchase Term Templates</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        // Opening an app lands on its default action (Purchase Orders) and
        // switching to another action is asynchronous: the previous list stays
        // mounted for a few frames. Without this wait, `.o_list_button_add`
        // would click the *previous* list's "New" button and create a purchase
        // order instead of a term template.
        waitForAction("Purchase Term Templates"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new term template."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the template name (e.g. Standard Delivery To)."),
            run: "edit Standard Delivery " + Date.now(),
        },
        {
            trigger: ".o_field_widget[name='term_type'] .o_select_menu_toggler",
            content: markup(_t(
                "Choose the <b>Term Type</b> (warranty, delivery to, payment, shipment, weight)."
            )),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item",
            content: _t("Pick a term type from the list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='content'] textarea",
            content: _t("Type the standard wording printed on purchase orders."),
            run: "edit ส่งของที่คลังสินค้าบริษัทภายใน 15 วัน",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        // --- Apply on a purchase order ---
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
            trigger: ".o_list_renderer",
            content: markup(_t(
                "On any purchase order open the <b>Terms</b> tab and pick the templates for " +
                "<b>Warranty</b>, <b>Delivery To</b>, <b>Payment Term</b>, <b>Shipment Term</b> " +
                "and <b>Weight Term</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "The combined term text is generated automatically and printed on the purchase order " +
                "and its PDF."
            )),
            run: "click",
        },
    ],
});
