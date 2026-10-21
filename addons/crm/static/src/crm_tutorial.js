import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tutorial.tutorials").add("crm_tutorial", [
    {
        model: "crm.lead",
        steps: [
            {
                action: "click",
                content: _t("Got a new lead? Click here to create your first opportunity."),
                trigger:
                    ".o_control_panel .o-kanban-button-new, .o_kanban_group .o_kanban_quick_add",
                type: "action",
            },
            {
                content: _t("What's the deal about? Give your opportunity a name."),
                name: "name",
                type: "field",
            },
            {
                content: _t(
                    "Who is it for? Type a few letters to find your customer, or create a new one."
                ),
                name: "partner_id",
                type: "field",
            },
            {
                content: _t("How much could this deal bring in? Enter the expected revenue."),
                name: "expected_revenue",
                type: "field",
            },
            {
                content: _t(
                    "Is it a promising one? Add stars to make it stand out in your pipeline."
                ),
                name: "priority",
                type: "field",
            },
            {
                action: "click",
                content: _t("Looking good! Now open the opportunity to see all its details."),
                trigger: ".o_kanban_quick_create .o_kanban_edit",
                type: "action",
            },
        ],
        viewType: "kanban",
    },
    {
        model: "crm.lead",
        steps: [
            {
                content: _t(
                    "Add tags to sort your opportunities at a glance (e.g. Product, Services)."
                ),
                name: "tag_ids",
                type: "field",
            },
            {
                content: _t("Note what your customer needs, so nothing gets forgotten."),
                name: "description",
                type: "field",
            },
            {
                action: "click",
                content: _t(
                    "Send a message to your customer right from here: they receive it by email."
                ),
                trigger: ".o-mail-Chatter-sendMessage",
                type: "action",
            },
            {
                content: _t(
                    "Making progress? Move the opportunity to the next stage of your pipeline."
                ),
                name: "stage_id",
                type: "field",
            },
            {
                action: "click",
                content: _t("Opportunity lost for good? Open the actions menu."),
                trigger: ".o_cp_action_menus button[data-hotkey='u']",
                type: "action",
            },
            {
                action: "click",
                content: _t("You can delete it from here."),
                hint: true,
                trigger: ".o-dropdown--menu .o_menu_item:has([data-icon='delete'])",
                type: "action",
            },
        ],
        viewType: "form",
    },
]);
