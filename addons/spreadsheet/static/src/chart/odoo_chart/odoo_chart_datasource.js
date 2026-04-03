import { registries, constants } from "@odoo/o-spreadsheet";
import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import {
    onGeoOdooChartItemClick,
    onOdooChartItemClick,
    onSunburstOdooChartItemClick,
    onTreemapOdooChartItemClick,
    onWaterfallOdooChartItemClick,
} from "./odoo_chart_helpers";

const { chartDataSourceRegistry } = registries;
const { CHART_TYPES } = constants;

// Types not supported by odoo charts (at least for now)
const EXCLUDED_CHART_TYPES = ["scorecard", "gauge", "calendar"];

function generateDataSetId(dataSource, dataSet) {
    const identifiers = JSON.parse([...dataSet.identifiers][0]);
    const mainAxis = dataSource.metaData.groupBy[0];
    const dataSetId = identifiers
        .slice(1) // first groupBy is the horizontal axis
        .map((id) => {
            const [[fieldName, value]] = Object.entries(id);
            if (Array.isArray(value)) {
                return `{"${fieldName}":${value[0]}}`; // [id, display_name]
            }
            return `{"${fieldName}":${value}}`;
        })
        .join(",");
    return mainAxis + dataSetId;
}

chartDataSourceRegistry.add("odoo", {
    supportedChartTypes: Array.from(new Set(CHART_TYPES).difference(new Set(EXCLUDED_CHART_TYPES))),
    fromExternalDefinition: (dataSource) => dataSource,
    fromContextCreation: (context) => context.dataSource,
    fromHierarchicalContextCreation: (context) => context.dataSource,
    validate: (dataSource) => CommandResult.Success,
    transform: (dataSource) => dataSource,
    extractData: (dataSource, chartId, getters) => {
        const { datasets, labels } = getters.getChartDataSource(chartId).getData();
        for (const ds of datasets) {
            if (ds.cumulatedStart) {
                ds.data[0] += ds.cumulatedStart;
            }
        }
        return {
            dataSetsValues: datasets.map((ds) => ({
                ...ds,
                data: ds.data.map((d) => ({ value: d })),
                dataSetId: generateDataSetId(dataSource, ds),
            })),
            labelValues: labels.map((l) => ({ value: l })),
        };
    },
    extractHierarchicalData: (dataSource, chartId, getters) => {
        const { datasets, labels } = getters.getChartDataSource(chartId).getHierarchicalData();
        return {
            dataSetsValues: datasets.map((ds) => ({
                ...ds,
                data: ds.data.map((d) => ({ value: d })),
                dataSetId: generateDataSetId(dataSource, ds),
            })),
            labelValues: labels.map((l) => ({ value: l })),
        };
    },
    onDataSetHover: (chartType, event, items, chart) => {
        if (!event.native) {
            return;
        }
        if (!items.length) {
            event.native.target.style.cursor = "";
            return;
        }
        const item = items[0];
        switch (chartType) {
            case "geo": {
                const data = chart.data.datasets?.[item.datasetIndex]?.data?.[item.index];
                if (
                    typeof data === "object" &&
                    data &&
                    "value" in data &&
                    data.value !== undefined
                ) {
                    event.native.target.style.cursor = "pointer";
                } else {
                    event.native.target.style.cursor = "";
                }
                break;
            }
            default: {
                if (items.length > 0) {
                    event.native.target.style.cursor = "pointer";
                } else {
                    event.native.target.style.cursor = "";
                }
            }
        }
    },
    onDataSetClick: (chartType, chartId, event, items, chartJSChart, getters) => {
        switch (chartType) {
            case "geo":
                return onGeoOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            case "sunburst":
                return onSunburstOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            case "treemap":
                return onTreemapOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            case "waterfall":
                return onWaterfallOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
            default:
                return onOdooChartItemClick(getters, chartId)(event, items, chartJSChart);
        }
    },
    adaptRanges: (dataSource) => dataSource,
    getDefinition: (dataSource) => dataSource,
    duplicateInDuplicatedSheet: (dataSource) => dataSource,
    getContextCreation: (dataSource) => ({ dataSource }),
    getHierarchicalContextCreation: (dataSource) => ({ dataSource }),
    toExcelDataSets: () => undefined,
});
