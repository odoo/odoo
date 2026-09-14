// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { SearchModelEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

const cogMenuRegistry = registry.category("cogMenu");

export class ExportAll extends Component {
    static template = "web.ExportAll";
    static components = { CogMenuItem };
    static props = {};

    async onDirectExportData() {
        this.env.searchModel.trigger(SearchModelEvent.DIRECT_EXPORT_DATA);
    }
}

const exportAllItem = /** @type {any} */ ({
    Component: ExportAll,
    groupNumber: COG_GROUP.DATA,
    isDisplayed: async (/** @type {any} */ env) =>
        ["kanban", "list"].includes(env.config.viewType) &&
        !env.model.root.selection.length &&
        (await user.hasGroup("base.group_allow_export")) &&
        exprToBoolean(env.config.viewArch.getAttribute("export_xlsx"), true),
});

cogMenuRegistry.add("export-all-menu", exportAllItem, { sequence: 20 });
