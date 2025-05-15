import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class SynchronizeMenu extends Component {
    static template = "base_import.SynchronizeMenu";
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }



    async syncMenus() {
        this.notification.add("Synchronisation des menus en cours...", { type: "info" });
        try {
            const response = await fetch('/sync_menus', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });

            if (!response.ok) {
                this.notification.add("Échec de la synchronisation des menus.", { type: "danger" });
                throw new Error('Failed to call the endpoint to synchronize menus');
            }

            const data = await response.json();
            this.notification.add("Synchronisation des menus terminée avec succès.", { type: "success" });
            return data;

        } catch (error) {
            console.error("Error:", error);
            this.notification.add("Une erreur s'est produite lors de la synchronisation des menus.", { type: "danger" });
        }
    }
}
function parseBoolean(value) {
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
        return ["1", "true", "True", "TRUE"].includes(value);
    }
    return false;
    }
export const synchroniseMenuItem = {

    Component: SynchronizeMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, isSmall }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
        parseBoolean(config.viewArch.getAttribute("synchronize") || "true") &&
        parseBoolean(config.viewArch.getAttribute("create") || "true"),
};

cogMenuRegistry.add("synchronize-menu", synchroniseMenuItem, { sequence: 2 });
