/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { TRIGGER_FILTERS } from "./utils";

const SUPPORTED_TRIGGERS = [
    "on_stage_set",
    "on_tag_set",
    "on_state_set",
    "on_priority_set",
    "on_user_set",
    "on_archive",
];

function enrichContext(context, group) {
    const { displayName, groupByField, value } = group;
    const { name, relation, type: ttype } = groupByField;
    for (const trigger of SUPPORTED_TRIGGERS) {
        if (!TRIGGER_FILTERS[trigger]({ name, relation, ttype })) {
            continue;
        }
        switch (trigger) {
            case "on_stage_set":
                return {
                    ...context,
                    default_trigger: trigger,
                    default_name: _t('Stage is set to "%s"', displayName),
                    default_trg_field_ref: value,
                };
            case "on_tag_set":
                return {
                    ...context,
                    default_trigger: trigger,
                    default_name: _t('"%s" tag is added', displayName),
                    default_trg_field_ref: value,
                };
            default:
                return { ...context, default_trigger: trigger };
        }
    }

    // Default trigger
    return { ...context, default_trigger: "on_create_or_write" };
}

patch(KanbanHeader.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.user = useService("user");
    },

    /**
     * @override
     */
    get permissions() {
        const permissions = super.permissions;
        Object.defineProperty(permissions, "canEditAutomations", {
            get: () => this.user.isAdmin,
            configurable: true,
        });
        return permissions;
    },

    async openAutomations() {
        return this._openAutomations();
    },

    async _openAutomations() {
        const domain = [["model", "=", this.props.list.resModel]];
        const modelId = await this.orm.search("ir.model", domain, { limit: 1 });
        const context = {
            active_test: false,
            default_model_id: modelId[0],
            search_default_model_id: modelId[0],
        };
        this.action.doAction("base_automation.base_automation_act", {
            additionalContext: enrichContext(context, this.group),
        });
    },
});

registry.category("kanban_header_config_items").add(
    "open_automations",
    {
        label: _t("Automations"),
        method: "openAutomations",
        isVisible: ({ permissions }) => permissions.canEditAutomations,
        class: "o_column_automations",
    },
    { sequence: 25, force: true }
);
