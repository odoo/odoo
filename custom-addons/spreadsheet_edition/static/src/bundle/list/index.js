/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { initCallbackRegistry } from "@spreadsheet/o_spreadsheet/init_callbacks";

import "./autofill";
import "./operational_transform";

import { ListingAllSidePanel } from "./side_panels/listing_all_side_panel";
import { ListAutofillPlugin } from "./plugins/list_autofill_plugin";

import { insertList } from "./list_init_callback";

const { featurePluginRegistry, sidePanelRegistry, cellMenuRegistry } = spreadsheet.registries;

featurePluginRegistry.add("odooListAutofillPlugin", ListAutofillPlugin);

sidePanelRegistry.add("LIST_PROPERTIES_PANEL", {
    title: () => _t("List properties"),
    Body: ListingAllSidePanel,
});

initCallbackRegistry.add("insertList", insertList);

cellMenuRegistry.add("listing_properties", {
    name: _t("See list properties"),
    sequence: 190,
    execute(env) {
        const position = env.model.getters.getActivePosition();
        const listId = env.model.getters.getListIdFromPosition(position);
        env.model.dispatch("SELECT_ODOO_LIST", { listId });
        env.openSidePanel("LIST_PROPERTIES_PANEL", {});
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        return env.model.getters.isExistingList(env.model.getters.getListIdFromPosition(position));
    },
    icon: "o-spreadsheet-Icon.ODOO_LIST",
});
