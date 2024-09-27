/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import PurchaseAdditionalTourSteps from "@purchase/js/tours/purchase_steps";
import { queryFirst } from "@odoo/hoot-dom";

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
            isActive: ["auto"],
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Let's create your first request for quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_form_editable .o_field_many2one[name='partner_id'] input",
            content: _t("Search a vendor name, or create one on the fly."),
            tooltipPosition: "bottom",
            run: "edit Agrolait",
        },
        {
            isActive: ["auto"],
            trigger: ".ui-menu-item > a",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_field_many2one[name='partner_id'] .o_external_button",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            content: _t("Add some products or services to your quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_field_widget[name=product_id], .o_field_widget[name=product_template_id]",
            content: _t("Select a product, or create a new one on the fly."),
            tooltipPosition: "right",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("DESK0001", input || this.anchor);
                const descriptionElement = queryFirst('.o_form_editable textarea[name="name"]');
                // when description changes, we know the product has been created
                descriptionElement.addEventListener("change", () => {
                    descriptionElement.classList.add("product_creation_success");
                });
            },
        },
        {
            isActive: ["auto"],
            trigger: '.ui-menu.ui-widget .ui-menu-item a:contains("DESK0001")',
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: '.o_form_editable textarea[name="name"].product_creation_success',
        },
        {
            isActive: ["auto"],
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_form_editable input[name='product_qty'] ",
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
            trigger: ".modal-content input[name='email']",
            run: "edit agrolait@example.com",
        },
        {
            isActive: ["auto"],
            trigger: ".modal-footer button[name='action_send_mail']",
        },
        {
            trigger: ".modal-footer button[name='action_send_mail']",
            content: _t("Send the request for quotation to your vendor."),
            tooltipPosition: "left",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_purchase_order",
        },
        {
            trigger: ".o_field_widget [name=price_unit]",
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
