import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { showProductColumn } from "@account/js/tours/tour_utils";

registry.category("web_tour.tours").add("sale_tour", {
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
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_sale_order",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_kanban_mobile",
        },
        {
            isActive: ["auto", "desktop"],
            trigger: "button.o_list_button_add",
            content: _t("Build your first quotation right here!"),
            run: async function ({ anchor, waitFor }) {
                // sale_management turns this button into a dropdown when
                // quotation templates exist. Keep this in one step: split
                // across two steps, the popover closes itself before the
                // second step's click can land.
                if (anchor.classList.contains("dropdown")) {
                    anchor.click();
                    const newQuotationButton = await waitFor(
                        "div.o_popover:has(.o_sale_management_template) > button.o-dropdown-item:not(.o_sale_management_template)"
                    );
                    newQuotationButton.click();
                } else {
                    anchor.click();
                }
            },
        },
        {
            isActive: ["manual", "desktop"],
            trigger: "button.o_list_button_add",
            content: _t("Build your first quotation right here!"),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: "button.o-kanban-button-new",
            content: _t("Build your first quotation right here!"),
            run: "click",
        },
        {
            trigger: ".o_sale_order",
        },
        ...stepUtils.searchOrCreateMany2X(
            ".o_field_res_partner_many2one[name='partner_id'] input",
            "customer",
            "Agrolait",
            {
                name: "Agrolait",
                email: "agrolait@example.com",
            }
        ),
        // as we are creating product on the fly in next step, which is not supported in sol_label_text
        ...showProductColumn("product_template_id"),
        {
            isActive: ["desktop"],
            trigger: ".o_field_x2many_list_row_add > button",
            content: _t("Click here to add some products or services to your quotation."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: 'button:contains("Add Line")',
            content: _t("Click here to add some products or services to your quotation."),
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_sale_order",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_form_button_save",
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
            trigger: "[data-icon='east']", // Wait for product creation
        },
        {
            isActive: ["desktop"],
            trigger: ".o_field_widget[name='price_unit'] input",
            content: _t("add the price of your product."),
            tooltipPosition: "right",
            run: "edit 10.0 && click body",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_field_cell[name='price_subtotal']:contains(10.00)",
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_field_widget[name='price_unit'] input",
            content: _t("add the price of your product."),
            tooltipPosition: "right",
            run: "edit 10.0",
        },
        {
            isActive: ["mobile"],
            trigger: ".modal .o_form_button_save",
            content: _t("Save the line."),
            run: "click",
        },
        {
            isActive: ["mobile"],
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
            run: "click",
        },
        {
            trigger: ".modal-footer button.o_mail_send",
            content: _t("Go ahead and send the quotation."),
            run: "click",
        },
        {
            trigger: "body:not(.modal-open)",
        },
    ],
});
