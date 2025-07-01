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
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Let's create your first request for quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            content: _t("Search a vendor name, or create one on the fly."),
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("Azure Interior", input || this.anchor);
            },
        },
        {
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Azure Interior')",
            run: "click",
        },
        {
            trigger: ".o_field_res_partner_many2one[name='partner_id'] .o_external_button",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            content: _t("Add some products or services to your quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_field_widget[name=product_id], .o_field_widget[name=product_template_id]",
            content: _t("Select a product, or create a new one on the fly."),
            tooltipPosition: "right",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("DESK0001", input || this.anchor);
            },
        },
        {
            isActive: ["auto"],
            trigger: "a:contains('DESK0001')",
            run: "click",
        },
        {
            trigger: ".o_field_text[name='name'] textarea:value(DESK0001)",
        },
        {
            trigger: ".o_purchase_order",
        },
        {
            trigger: "div.o_field_widget[name='product_qty'] input ",
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
            trigger: ".modal-footer button[name='action_send_mail']",
        },
        {
            trigger: ".modal-footer button[name='action_send_mail']",
            content: _t("Send the request for quotation to your vendor."),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_purchase_order",
        },
        {
            content: "Select price",
            trigger: 'tbody tr.o_data_row .o_list_number[name="price_unit"]',
        },
        {
            trigger: "tbody tr.o_data_row .o_list_number[name='price_unit']",
            content: _t(
                "Once you get the price from the vendor, you can complete the purchase order with the right price."
            ),
            tooltipPosition: "right",
            run: "edit 200.00",
        },
        {
            isActive: ["auto"],
            trigger: ".o_purchase_order",
            run: "click",
        },
        ...stepUtils.statusbarButtonsSteps("Confirm Order", _t("Confirm your purchase.")),
        ...new PurchaseAdditionalTourSteps()._get_purchase_stock_steps(),
    ],
});
