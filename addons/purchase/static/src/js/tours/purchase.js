/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import PurchaseAdditionalTourSteps from "@purchase/js/tours/purchase_steps";

registry.category("web_tour.tours").add("purchase_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            isActive: ["community"],
            trigger: '.o_app[data-menu-xmlid="purchase.menu_purchase_root"]',
            content: _t(
                "Let's try the Purchase app to manage the flow from purchase to reception and invoice control."
            ),
            tooltipPosition: "right",
            run: "click",
        },
        {
            isActive: ["enterprise"],
            trigger: '.o_app[data-menu-xmlid="purchase.menu_purchase_root"]',
            content: _t(
                "Let's try the Purchase app to manage the flow from purchase to reception and invoice control."
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_purchase_order .o_list_button_add",
            content: _t("Let's create your first request for quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_purchase_order .o_form_editable div[name='partner_id'] input",
            content: _t("Search a vendor name, or create one on the fly."),
            tooltipPosition: "bottom",
            run: "edit Agrolait",
        },
        {
            isActive: ["auto"],
            content: "Choose the first item in suggestions menu",
            trigger: ".ui-menu-item > a",
            run: "click",
        },
        {
            isActive: ["auto"],
            content: "Check external button is well in DOM",
            trigger: ".o_purchase_order .o_form_editable div[name='partner_id'] .o_external_button",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            content: _t("Add some products or services to your quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger:
                ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
            content: _t("Select a product, or create a new one on the fly."),
            tooltipPosition: "right",
            run: "edit DESK0001",
        },
        {
            isActive: ["auto"],
            content: "Create DESK0001 item",
            trigger: `.dropdown-menu li:first`,
            run: "click",
        },
        {
            trigger: ".o_purchase_order .o_form_editable div[name='product_qty'] input",
            content: _t("Indicate the product quantity you want to order."),
            tooltipPosition: "right",
            run: "edit 12.0",
        },
        {
            isActive: ["auto", "mobile"],
            trigger: ".o_statusbar_buttons .o_arrow_button_current[name='action_rfq_send']",
        },
        ...stepUtils.statusbarButtonsSteps(
            "Send by Email",
            _t("Send the request for quotation to your vendor.")
        ),
        {
            content: _t("Write an email"),
            trigger: ".modal .modal-content div[name=email] input",
            run: "edit agrolait@example.com",
        },
        {
            content: _t("Save informations and close the modal"),
            trigger: ".modal .modal-footer button:contains(save & close)",
            run: "click",
        },
        {
            content: _t("Send the request for quotation to your vendor."),
            trigger: ".modal .modal-footer button:contains(send)",
            tooltipPosition: "left",
            run: "click",
        },
        {
            content: _t("Click on unit price to edit it"),
            trigger: ".o_purchase_order td[name=price_unit]",
            run: "click",
        },
        {
            content: _t(
                "Once you get the price from the vendor, you can complete the purchase order with the right price."
            ),
            trigger: ".o_purchase_order td[name=price_unit] input",
            tooltipPosition: "right",
            run: "edit 200.00",
        },
        ...stepUtils.statusbarButtonsSteps("Confirm Order", _t("Confirm your purchase.")),
        ...new PurchaseAdditionalTourSteps()._get_purchase_stock_steps(),
    ],
});
