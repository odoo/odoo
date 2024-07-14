/* @odoo-module */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { PromoteStudioAutomationDialog } from "@web_enterprise/webclient/promote_studio_dialog/promote_studio_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(KanbanHeader.prototype, {
    setup() {
        super.setup();
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
        if (typeof this._openAutomations === "function") {
            // this is the case if base_automation is installed
            return this._openAutomations();
        } else {
            this.env.services.dialog.add(PromoteStudioAutomationDialog, {
                title: _t("Odoo Studio - Customize workflows in minutes"),
            });
        }
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
