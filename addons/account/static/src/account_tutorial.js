import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tutorial.tutorials").add("account_tutorial", [
    {
        model: "account.journal",
        steps: [
            {
                action: "click",
                content: _t("Ready to get paid? Create your first invoice."),
                trigger: "[name='kanban_primary_left'] > button[name='action_create_new']",
                type: "action",
            },
        ],
        viewType: "kanban",
    },
    {
        context: { default_move_type: "out_invoice" },
        model: "account.move",
        steps: [
            {
                content: _t(
                    "Who are you invoicing? Type a few letters to find the customer, or create a new one."
                ),
                name: "partner_id",
                type: "field",
            },
            {
                content: _t("When should your customer pay? Set the due date or payment terms."),
                name: "invoice_date_due",
                type: "field",
            },
            {
                content: _t("Add a line for what you sell."),
                name: "invoice_line_ids",
                type: "field",
            },
            {
                content: _t("Describe the product or service you're invoicing."),
                name: "invoice_line_ids.label",
                type: "field",
            },
            {
                content: _t("How much does it cost? Enter its price."),
                name: "invoice_line_ids.price_unit",
                type: "field",
            },
            {
                action: "click",
                content: _t("Everything looks right? Confirm the invoice."),
                trigger: "button[name='action_post']",
                type: "action",
            },
            {
                action: "click",
                content: _t("From here, you can send the invoice to your customer by email."),
                hint: true,
                trigger: "button[name='action_invoice_sent']",
                type: "action",
            },
            {
                action: "click",
                content: _t("Just a test? Reset the invoice to draft to be able to delete it."),
                trigger: "button[name='button_draft']",
                type: "action",
            },
            {
                action: "click",
                content: _t("Then open the actions menu."),
                trigger: ".o_cp_action_menus button[data-hotkey='u']",
                type: "action",
            },
            {
                action: "click",
                content: _t("And delete it to keep your books clean."),
                trigger: ".o-dropdown--menu .o_menu_item:has([data-icon='delete'])",
                type: "action",
            },
        ],
        viewType: "form",
    },
]);
