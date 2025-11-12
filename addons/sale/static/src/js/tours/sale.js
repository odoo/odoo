import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("sale_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            isActive: ["community"],
            trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
            content: _t("Let’s create a beautiful quotation in a few clicks ."),
            tooltipPosition: "right",
            run: "click",
        },
        {
            isActive: ["enterprise"],
            trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
            content: _t("Let’s create a beautiful quotation in a few clicks ."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_sale_order",
        },
        {
            trigger: "button.o_list_button_add",
            content: _t("Build your first quotation right here!"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_sale_order",
        },
        {
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            content: _t("Search a customer name, or create one on the fly."),
            tooltipPosition: "right",
            run: "edit Agrolait",
        },
        {
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Agrolait')",
            run: "click",
        },
        {
            trigger: ".o_field_x2many_list_row_add > button",
            content: _t("Click here to add some products or services to your quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_sale_order",
        },
        {
            trigger: `
                .o_field_widget[name='product_id'] input,
                .o_field_widget[name='product_template_id'] input
            `,
            content: _t("Select a product, or create a new one on the fly."),
            tooltipPosition: "right",
            run: "edit DESK0001",
        },
        {
            isActive: ["auto"],
            trigger: "a:contains('DESK0001')",
            run: "click",
        },
        {
            trigger: ".oi-arrow-right", // Wait for product creation
        },
        {
            trigger: ".o_field_widget[name='price_unit'] input",
            content: _t("add the price of your product."),
            tooltipPosition: "right",
            run: "edit 10.0 && click body",
        },
        {
            isActive: ["auto"],
            trigger: ".o_field_cell[name='price_subtotal']:contains(10.00)",
            run: "click",
        },
        {
            isActive: ["auto", "mobile"],
            trigger: ".o_statusbar_buttons button[name='action_quotation_send']",
        },
        ...stepUtils.statusbarButtonsSteps(
            "Send",
            markup(_t("<b>Send the quote</b> to yourself and check what the customer will receive.")),
        ),
        {
            isActive: ["body:not(:has(.modal-footer button.o_mail_send))"],
            trigger: ".modal-footer button[name='document_layout_save']",
            content: _t("let's continue"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".modal-footer button.o_mail_send",
            content: _t("Go ahead and send the quotation."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: "body:not(.modal-open)",
            run: "click",
        },
    ],
});
