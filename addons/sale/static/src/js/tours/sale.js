/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("sale_tour", {
    url: "/web",
    rainbowMan: true,
    rainbowManMessage: () => markup(_t("<b>Congratulations</b>, your first quotation is sent!<br>Check your email to validate the quote.")),
    sequence: 20,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            isActive: ["community"],
            trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
            content: _t("Let’s create a beautiful quotation in a few clicks ."),
            position: "right",
            run: "click",
        },
        {
            isActive: ["enterprise"],
            trigger: ".o_app[data-menu-xmlid='sale.sale_menu_root']",
            content: _t("Let’s create a beautiful quotation in a few clicks ."),
            position: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_sale_order",
        },
        {
            trigger: "button.o_list_button_add",
            content: _t("Build your first quotation right here!"),
            position: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_sale_order",
        },
        {
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            content: _t("Search a customer name, or create one on the fly."),
            position: "right",
            run: "edit Agrolait",
        },
        {
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Agrolait')",
            in_modal: false,
            run: "click",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            content: _t("Click here to add some products or services to your quotation."),
            position: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_sale_order",
        },
        {
            trigger:
                ".o_field_widget[name='product_id'], .o_field_widget[name='product_template_id']",
            content: _t("Select a product, or create a new one on the fly."),
            position: "right",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("DESK0001", input || this.anchor);
                const descriptionElement = document.querySelector(
                    ".o_form_editable textarea[name='name']"
                );
                // when description changes, we know the product has been created
                if (descriptionElement) {
                    descriptionElement.addEventListener("change", () => {
                        descriptionElement.classList.add("product_creation_success");
                    });
                }
            },
            id: "product_selection_step",
        },
        {
            isActive: ["auto"],
            trigger: "a:contains('DESK0001')",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ".o_field_text[name='name'] textarea:value(DESK0001)",
        },
        {
            isActive: ["auto"],
            trigger: ".oi-arrow-right", // Wait for product creation
        },
        {
            trigger: ".o_field_widget[name='price_unit'] input",
            content: _t("add the price of your product."),
            position: "right",
            run: "edit 10.0 && click .o_selected_row",
        },
        {
            isActive: ["auto"],
            trigger: ".o_field_monetary[name='price_subtotal']:contains(10.00)",
            run: "click",
        },
        {
            isActive: ["auto", "mobile"],
            trigger: ".o_statusbar_buttons button[name='action_quotation_send']",
        },
        ...stepUtils.statusbarButtonsSteps(
            "Send by Email",
            markup(_t("<b>Send the quote</b> to yourself and check what the customer will receive.")),
        ),
        {
            isActive: ["body:not(:has(.modal-footer button[name='action_send_mail']))"],
            trigger: ".modal-footer button[name='document_layout_save']",
            content: _t("let's continue"),
            position: "bottom",
            run: "click",
        },
        {
            trigger: ".modal-footer button[name='action_send_mail']",
            content: _t("Go ahead and send the quotation."),
            position: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: "body:not(.modal-open)",
            run: "click",
        },
    ],
});
