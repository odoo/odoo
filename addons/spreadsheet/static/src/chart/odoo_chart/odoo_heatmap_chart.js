import { registries } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { chartTypeRegistry, chartDataSourceRegistry } = registries;

const HeatmapChart = chartTypeRegistry.get("heatmap");

HeatmapChart.allowedDefinitionKeys.push("dataSource");

patch(chartDataSourceRegistry.get("none"), {
    fromExternalDefinition() {
        return undefined;
    },
});

patch(HeatmapChart, {
    getContextCreation(definition) {
        if (definition.dataSource?.type === "odoo") {
            return definition;
        }
        return super.getContextCreation(...arguments);
    },

    getDefinitionFromContextCreation(context, dataSourceBuilder) {
        const definition = super.getDefinitionFromContextCreation(...arguments);
        if (context.dataSource?.type === "odoo") {
            return { ...definition, dataSource: dataSourceBuilder.fromContextCreation(context) };
        }
        return definition;
    },

    getRuntime(getters, definition, dataSourceExtractor, sheetId, eventHandlers, colorTheme) {
        if (definition.dataSource?.type !== "odoo") {
            return super.getRuntime(...arguments);
        }
        const { labelValues, dataSetsValues } = dataSourceExtractor.extractData();
        const rows = [];
        const columns = [];
        const values = [];
        // Iterate column by column to keep the order of the data source: the heatmap orders its
        // rows and columns by first occurrence, and the data source data sets are created in that
        // same order.
        for (let i = 0; i < labelValues.length; i++) {
            for (const dataSet of dataSetsValues) {
                // The data source fills the missing (row, column) combinations with 0 and an
                // empty domain. Skip them so they're displayed as missing values.
                if (!dataSet.domains[i].length) {
                    continue;
                }
                rows.push({ value: dataSet.label });
                columns.push(labelValues[i]);
                values.push(dataSet.data[i]);
            }
        }
        const heatmapGetters = Object.create(getters);
        heatmapGetters.getVisibleRangeValues = (rangeValues) => rangeValues;
        const runtime = super.getRuntime(
            heatmapGetters,
            {
                ...definition,
                xRange: columns,
                yRange: rows,
                sizeRange: values,
                dataSetsHaveTitle: false,
            },
            dataSourceExtractor,
            sheetId,
            eventHandlers,
            colorTheme
        );
        runtime.chartJsConfig.options = { ...runtime.chartJsConfig.options, ...eventHandlers };
        return runtime;
    },
});
