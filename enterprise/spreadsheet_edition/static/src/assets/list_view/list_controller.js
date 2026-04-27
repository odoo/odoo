/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

export const patchListControllerExportSelection = {
    setup() {
        super.setup();
        this.canInsertInSpreadsheet = session.can_insert_in_spreadsheet;
    },
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems(...arguments);
        menuItems["insert"] = {
            isAvailable: () => this.canInsertInSpreadsheet,
            sequence: 15,
            icon: "oi oi-view-list",
            description: _t("Insert in spreadsheet"),
            callback: () => this.env.bus.trigger("insert-list-spreadsheet"),
        };
        return menuItems;
    },
};

export const unpatchListControllerExportSelection = patch(
    ListController.prototype,
    patchListControllerExportSelection
);
