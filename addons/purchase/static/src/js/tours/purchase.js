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
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            content: _t("Search a vendor name, or create one on the fly."),
            tooltipPosition: "bottom",
            run: "edit Azure Interior",
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
            trigger: ".o_field_x2many_list_row_add > button",
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
            run: "edit DESK0001",
        },
        {
            content: _t("Let's create it."),
            trigger: "a:contains('DESK0001')",
            run: "click",
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
            "Send RFQ",
            _t("Send the request for quotation to your vendor.")
        ),
        {
            content: _t(`Don't forget to set the Azure Interior's email.`),
            trigger: ".o_popover .o-mail-RecipientsInputTagsListPopover input",
            run: "edit kevin@example.com",
        },
        {
            content: _t(`Let's confirm it.`),
            trigger: `.o_popover button:contains(${_t("Set email")})`,
            run: "click",
        },
        {
            trigger: ".modal-footer button[name='action_send_mail']",
            content: _t("Send the request for quotation to your vendor."),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: `body:not(:has(.modal))`,
        },
        {
            content: _t(
                "Once you get the price from the vendor, you can complete the purchase order with the right price."
            ),
            trigger: "tbody tr.o_data_row td[name='price_unit']",
            run: "click",
        },
        {
            trigger: "tbody tr.o_data_row td[name='price_unit'] input",
            content: _t(
                "Once you get the price from the vendor, you can complete the purchase order with the right price."
            ),
            tooltipPosition: "right",
            run: "edit 200.00",
        },
        ...stepUtils.statusbarButtonsSteps("Confirm Order", _t("Confirm your purchase.")),
        ...new PurchaseAdditionalTourSteps()._get_purchase_stock_steps(),
    ],
});
