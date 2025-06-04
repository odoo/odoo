/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { SynchronizeDialog } from "./synchronize_dialog";

const cogMenuRegistry = registry.category("cogMenu");

export class SynchronizeMenu extends Component {
    static template = "base_import.SynchronizeMenuByRange";
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
    }

    async syncMenusByRange() {
        this.dialogService.add(SynchronizeDialog, {
            confirm: async (skip, limit) => {
                this.notification.add("Synchronisation des menus par plage en cours...", { type: "info" });
                try {
                    const response = await fetch('/sync_menus_by_range', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': odoo.csrf_token, // Add CSRF token for security
                        },
                        body: JSON.stringify({
                            skip: parseInt(skip),
                            limit: parseInt(limit)
                        }),
                    });

                    if (!response.ok) {
                        throw new Error('Failed to call the endpoint to synchronize menus');
                    }

                    const data = await response.json();
                    this.notification.add("Synchronisation des menus terminée avec succès.", { type: "success" });
                    return data;

                } catch (error) {
                    console.error("Error:", error);
                    this.notification.add("Une erreur s'est produite lors de la synchronisation des menus.", { type: "danger" });
                }
            },
        });
    }
}
/* This function From Odoo 17 */
 function archParseBoolean(str, trueIfEmpty = false) {
    return str ? !/^false|0$/i.test(str) : trueIfEmpty;
}

export const synchroniseMenuItem = {
    Component: SynchronizeMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, isSmall }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
        archParseBoolean(config.viewArch.getAttribute("synchronize"), true) &&
        archParseBoolean(config.viewArch.getAttribute("create"), true),
};

cogMenuRegistry.add("synchronize-menu-by-range", synchroniseMenuItem, { sequence: 3 });