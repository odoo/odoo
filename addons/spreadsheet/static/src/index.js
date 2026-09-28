/**
 * This file is meant to load the different subparts of the module
 * to guarantee their plugins are loaded in the right order
 *
 * dependency:
 *             other plugins
 *                   |
 *                  ...
 *                   |
 *                filters
 *                /\    \
 *               /  \    \
 *           pivot  list  Odoo chart
 */

/** TODO: Introduce a position parameter to the plugin registry in order to load them in a specific order */
import * as spreadsheet from "@odoo/o-spreadsheet";

const { corePluginRegistry, evaluationPluginRegistry, featurePluginRegistry } =
    spreadsheet.registries;

import {
    GlobalFiltersCorePlugin,
    GlobalFiltersUIPlugin,
    GlobalFiltersCoreViewPlugin,
} from "@spreadsheet/global_filters/index";
import { PivotOdooCorePlugin, PivotCoreViewGlobalFilterPlugin } from "@spreadsheet/pivot/index"; // pivot depends on filter for its getters
import { ListCorePlugin, ListCoreViewPlugin, ListUIPlugin } from "@spreadsheet/list/index"; // list depends on filter for its getters
import {
    ChartOdooLinkPlugin,
    OdooChartCorePlugin,
    OdooChartCoreViewPlugin,
} from "@spreadsheet/chart/index"; // Odoochart depends on filter for its getters
import { PivotCoreGlobalFilterPlugin } from "./pivot/plugins/pivot_core_global_filter_plugin";
import { PivotOdooUIPlugin } from "./pivot/plugins/pivot_odoo_ui_plugin";
import { ListCoreGlobalFilterPlugin } from "./list/plugins/list_core_global_filter_plugin";
import { OdooChartFeaturePlugin } from "./chart/plugins/odoo_chart_feature_plugin";
import { LoggingUIPlugin } from "@spreadsheet/logging/logging_ui_plugin";
import { PivotOdooCoreViewPlugin } from "./pivot/plugins/pivot_odoo_core_view_plugin";

corePluginRegistry.add("PivotOdooCorePlugin", PivotOdooCorePlugin);
corePluginRegistry.add("OdooListCorePlugin", ListCorePlugin);
corePluginRegistry.add("OdooGlobalFiltersCorePlugin", GlobalFiltersCorePlugin);
corePluginRegistry.add("OdooPivotGlobalFiltersCorePlugin", PivotCoreGlobalFilterPlugin);
corePluginRegistry.add("OdooListCoreGlobalFilterPlugin", ListCoreGlobalFilterPlugin);
corePluginRegistry.add("odooChartCorePlugin", OdooChartCorePlugin);
corePluginRegistry.add("ChartOdooLinkPlugin", ChartOdooLinkPlugin);

// local command handled by the list and Odoo chart core view plugins, which are
// evaluation plugins: it has to be declared as an evaluation command to reach them.
spreadsheet.evaluationCommandTypes.add("REFRESH_ALL_DATA_SOURCES");

evaluationPluginRegistry.add("OdooGlobalFiltersCoreViewPlugin", GlobalFiltersCoreViewPlugin);
evaluationPluginRegistry.add(
    "OdooPivotGlobalFiltersCoreViewPlugin",
    PivotCoreViewGlobalFilterPlugin
);
evaluationPluginRegistry.add("OdooListCoreViewPlugin", ListCoreViewPlugin);
evaluationPluginRegistry.add("OdooChartCoreViewPlugin", OdooChartCoreViewPlugin);
evaluationPluginRegistry.add("PivotOdooCoreViewPlugin", PivotOdooCoreViewPlugin);

featurePluginRegistry.add("OdooLoggingUIPlugin", LoggingUIPlugin);
featurePluginRegistry.add("OdooGlobalFiltersUIPlugin", GlobalFiltersUIPlugin);
featurePluginRegistry.add("odooPivotUIPlugin", PivotOdooUIPlugin);
featurePluginRegistry.add("odooListUIPlugin", ListUIPlugin);
featurePluginRegistry.add("OdooChartFeaturePlugin", OdooChartFeaturePlugin);
