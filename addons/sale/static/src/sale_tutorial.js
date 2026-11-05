import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tuto.tutorials").add("sale_tutorial", [
    {
        model: "sale.order",
        steps: [
            {
                action: "click",
                content: _t("Ready to sell? Build your first quotation right here."),
                trigger: ".o_control_panel .o_list_button_add",
                type: "action",
            },
        ],
        viewType: "list",
    },
    {
        model: "sale.order",
        steps: [
            {
                content: _t(
                    "Who is it for? Type a few letters to find your customer, or create a new one."
                ),
                name: "partner_id",
                type: "field",
            },
            {
                content: _t("What are you selling? Add a line to your quotation."),
                name: "order_line",
                type: "field",
            },
            {
                content: _t("Type a description, or search for an existing product."),
                name: "order_line.label",
                type: "field",
            },
            {
                content: _t("How many? Set the quantity."),
                name: "order_line.product_uom_qty",
                type: "field",
            },
            {
                content: _t("Check the price, and adjust it if needed."),
                name: "order_line.price_unit",
                type: "field",
            },
            {
                action: "click",
                content: _t(
                    "All set? From here, you can send the quotation to your customer by email."
                ),
                hint: true,
                trigger: "button[name='action_quotation_send']",
                type: "action",
            },
        ],
        viewType: "form",
    },
]);
