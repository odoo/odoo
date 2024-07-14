/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { initCallbackRegistry } from "@spreadsheet/o_spreadsheet/init_callbacks";

import { PivotAutofillPlugin } from "./plugins/pivot_autofill_plugin";
import { PivotSidePanel } from "./side_panels/pivot_list_side_panel";

import "./autofill";
import "./operational_transform";
import { insertPivot } from "./pivot_init_callback";

const { featurePluginRegistry, sidePanelRegistry, cellMenuRegistry } = spreadsheet.registries;

featurePluginRegistry.add("odooPivotAutofillPlugin", PivotAutofillPlugin);

sidePanelRegistry.add("PIVOT_PROPERTIES_PANEL", {
    title: () => _t("Pivot properties"),
    Body: PivotSidePanel,
});

initCallbackRegistry.add("insertPivot", insertPivot);

cellMenuRegistry.add("pivot_properties", {
    name: _t("See pivot properties"),
    sequence: 170,
    execute(env) {
        const position = env.model.getters.getActivePosition();
        const pivotId = env.model.getters.getPivotIdFromPosition(position);
        env.model.dispatch("SELECT_PIVOT", { pivotId });
        env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        return env.model.getters.isExistingPivot(env.model.getters.getPivotIdFromPosition(position));
    },
    icon: "o-spreadsheet-Icon.PIVOT",
});
