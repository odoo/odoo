import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

import PurchaseAdditionalTourSteps from "@purchase/js/tours/purchase_steps";

registry.category("web_tour.tours").add("purchase_tour", {
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
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_purchase_order",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_kanban_mobile",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_list_button_add",
            content: _t("Let's create your first request for quotation."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: "button.o-kanban-button-new",
            content: _t("Let's create your first request for quotation."),
            run: "click",
        },
        ...stepUtils.searchOrCreateMany2X(
            ".o_field_res_partner_many2one[name='partner_id'] input",
            "vendor",
            "Azure Interior",
            {
                name: "Azure Interior",
                email: "azure.interior@example.com",
            }
        ),
        {
            isActive: ["desktop"],
            trigger: ".o_field_x2many_list_row_add > button",
            content: _t("Add some products or services to your quotation."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: 'button:contains("Add product")',
            content: _t("Add some products or services to your quotation."),
            run: "click",
        },
        ...stepUtils.searchOrCreateMany2X(
            `
                .o_field_widget[name='product_id'] input,
                .o_field_widget[name='product_template_id'] input
            `,
            "product",
            "DESK0001",
            {
                name: "DESK0001",
            }
        ),
        {
            isActive: ["desktop"],
            trigger: "div.o_field_widget[name='product_qty'] input ",
            content: _t("Indicate the product quantity you want to order."),
            tooltipPosition: "right",
            run: "edit 12.0",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_field_widget[name='product_qty'] input",
            content: _t("Indicate the product quantity you want to order."),
            tooltipPosition: "right",
            run: "edit 12.0",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_form_button_save",
            content: _t("Save the line."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_statusbar_buttons button[name='action_rfq_send']",
        },
        ...stepUtils.statusbarButtonsSteps(
            "Send RFQ",
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
            isActive: ["desktop"],
            content: _t("Select price"),
            trigger: 'tbody tr.o_data_row .o_list_number[name="price_unit"]',
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: "tbody tr.o_data_row .o_list_number[name='price_unit'] input",
            content: _t(
                "Once you get the price from the vendor, you can complete the purchase order with the right price."
            ),
            tooltipPosition: "right",
            run: "edit 200.00",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_purchase_order",
            content: _t("Confirm the price."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: _t("Select price"),
            trigger: ".o_kanban_record",
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_field_widget[name='price_unit'] input",
            content: _t(
                "Once you get the price from the vendor, you can complete the purchase order with the right price."
            ),
            tooltipPosition: "right",
            run: "edit 200.00",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_form_button_save",
            content: _t("Save the line."),
            run: "click",
        },
        ...stepUtils.statusbarButtonsSteps("Confirm Order", _t("Confirm your purchase.")),
        {
            isActive: ["desktop"],
            trigger: ".o_statusbar_status .o_arrow_button_current:contains('Purchase Order')",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_statusbar_status button.dropdown-toggle:contains('Purchase Order')",
        },
        ...new PurchaseAdditionalTourSteps()._get_purchase_stock_steps(),
    ],
});
