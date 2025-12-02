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
import { _t } from "@web/core/l10n/translation";

const { corePluginRegistry, coreViewsPluginRegistry, featurePluginRegistry } =
    spreadsheet.registries;

import {
    GlobalFiltersCorePlugin,
    GlobalFiltersUIPlugin,
    GlobalFiltersCoreViewPlugin,
} from "@spreadsheet/global_filters/index";
import {
    PivotOdooCorePlugin,
    PivotCoreViewGlobalFilterPlugin,
    PivotUIGlobalFilterPlugin,
} from "@spreadsheet/pivot/index"; // list depends on filter for its getters
import { ListCorePlugin, ListCoreViewPlugin, ListUIPlugin } from "@spreadsheet/list/index"; // pivot depends on filter for its getters
import {
    ChartOdooMenuPlugin,
    OdooChartCorePlugin,
    OdooChartCoreViewPlugin,
} from "@spreadsheet/chart/index"; // Odoochart depends on filter for its getters
import { PivotCoreGlobalFilterPlugin } from "./pivot/plugins/pivot_core_global_filter_plugin";
import { PivotOdooUIPlugin } from "./pivot/plugins/pivot_odoo_ui_plugin";
import { ListCoreGlobalFilterPlugin } from "./list/plugins/list_core_global_filter_plugin";
import { globalFieldMatchingRegistry } from "./global_filters/helpers";
import { OdooChartFeaturePlugin } from "./chart/plugins/odoo_chart_feature_plugin";

globalFieldMatchingRegistry.add("pivot", {
    getIds: (getters) =>
        getters
            .getPivotIds()
            .filter(
                (id) =>
                    getters.getPivotCoreDefinition(id).type === "ODOO" &&
                    getters.getPivotFieldMatch(id)
            ),
    getDisplayName: (getters, pivotId) => getters.getPivotName(pivotId),
    getTag: (getters, pivotId) =>
        _t("Pivot #%(pivot_id)s", { pivot_id: getters.getPivotFormulaId(pivotId) }),
    getFieldMatching: (getters, pivotId, filterId) =>
        getters.getPivotFieldMatching(pivotId, filterId),
    getModel: (getters, pivotId) => {
        const pivot = getters.getPivotCoreDefinition(pivotId);
        return pivot.type === "ODOO" && pivot.model;
    },
    waitForReady: (getters) =>
        getters
            .getPivotIds()
            .map((pivotId) => getters.getPivot(pivotId))
            .filter((pivot) => pivot.type === "ODOO")
            .map((pivot) => pivot.loadMetadata()),
    getFields: (getters, pivotId) => getters.getPivot(pivotId).getFields(),
    getActionXmlId: (getters, pivotId) => getters.getPivotCoreDefinition(pivotId).actionXmlId,
});

globalFieldMatchingRegistry.add("list", {
    getIds: (getters) => getters.getListIds().filter((id) => getters.getListFieldMatch(id)),
    getDisplayName: (getters, listId) => getters.getListName(listId),
    getTag: (getters, listId) => _t(`List #%(list_id)s`, { list_id: listId }),
    getFieldMatching: (getters, listId, filterId) => getters.getListFieldMatching(listId, filterId),
    getModel: (getters, listId) => getters.getListDefinition(listId).model,
    waitForReady: (getters) =>
        getters.getListIds().map((listId) => getters.getListDataSource(listId).loadMetadata()),
    getFields: (getters, listId) => getters.getListDataSource(listId).getFields(),
    getActionXmlId: (getters, listId) => getters.getListDefinition(listId).actionXmlId,
});

globalFieldMatchingRegistry.add("chart", {
    getIds: (getters) => getters.getOdooChartIds(),
    getDisplayName: (getters, chartId) => getters.getOdooChartDisplayName(chartId),
    getFieldMatching: (getters, chartId, filterId) =>
        getters.getOdooChartFieldMatching(chartId, filterId),
    getModel: (getters, chartId) =>
        getters.getChart(chartId).getDefinitionForDataSource().metaData.resModel,
    getTag: async (getters, chartId) => {
        const chartModel = await getters.getChartDataSource(chartId).getModelLabel();
        return _t("Chart - %(chart_model)s", { chart_model: chartModel });
    },
    waitForReady: (getters) =>
        getters
            .getOdooChartIds()
            .map((chartId) => getters.getChartDataSource(chartId).loadMetadata()),
    getFields: (getters, chartId) => getters.getChartDataSource(chartId).getFields(),
    getActionXmlId: (getters, chartId) => getters.getChartDefinition(chartId).actionXmlId,
});

corePluginRegistry.add("OdooGlobalFiltersCorePlugin", GlobalFiltersCorePlugin);
corePluginRegistry.add("PivotOdooCorePlugin", PivotOdooCorePlugin);
corePluginRegistry.add("OdooPivotGlobalFiltersCorePlugin", PivotCoreGlobalFilterPlugin);
corePluginRegistry.add("OdooListCorePlugin", ListCorePlugin);
corePluginRegistry.add("OdooListCoreGlobalFilterPlugin", ListCoreGlobalFilterPlugin);
corePluginRegistry.add("odooChartCorePlugin", OdooChartCorePlugin);
corePluginRegistry.add("chartOdooMenuPlugin", ChartOdooMenuPlugin);

coreViewsPluginRegistry.add("OdooGlobalFiltersCoreViewPlugin", GlobalFiltersCoreViewPlugin);
coreViewsPluginRegistry.add(
    "OdooPivotGlobalFiltersCoreViewPlugin",
    PivotCoreViewGlobalFilterPlugin
);
coreViewsPluginRegistry.add("OdooListCoreViewPlugin", ListCoreViewPlugin);
coreViewsPluginRegistry.add("OdooChartCoreViewPlugin", OdooChartCoreViewPlugin);

featurePluginRegistry.add("OdooPivotGlobalFilterUIPlugin", PivotUIGlobalFilterPlugin);
featurePluginRegistry.add("OdooGlobalFiltersUIPlugin", GlobalFiltersUIPlugin);
featurePluginRegistry.add("odooPivotUIPlugin", PivotOdooUIPlugin);
featurePluginRegistry.add("odooListUIPlugin", ListUIPlugin);
featurePluginRegistry.add("OdooChartFeaturePlugin", OdooChartFeaturePlugin);
