import { navigateTo } from "@spreadsheet/actions/helpers";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";

export function onOdooChartItemClick(getters, chart) {
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem, chartData) => {
        const { datasets, labels } = chartData;
        const { datasetIndex, index } = chartJsItem;
        const dataset = datasets[datasetIndex];
        let name = labels[index];
        if (dataset.label) {
            name += ` / ${dataset.label}`;
        }
        return { name, domain: dataset.domains[index] };
    });
}

export function onWaterfallOdooChartItemClick(getters, chart) {
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem, chartData) => {
        const showSubtotals = chart.showSubTotals;
        const { datasets, labels } = chartData;

        // DataSource datasets are all merged in a single dataset in waterfall charts (with possibly subtotals)
        // We need to transform back the chartJS index to the DataSource index
        let datasetIndex = 0;
        let index = chartJsItem.index;
        for (const dataset of datasets) {
            const length = dataset.data.length + (showSubtotals ? 1 : 0);
            if (index < length) {
                break;
            } else {
                datasetIndex++;
                index -= length;
            }
        }

        const dataset = datasets[datasetIndex];
        let name = labels[index];
        if (dataset.label) {
            name += ` / ${dataset.label}`;
        }
        let domain = dataset.domains[index];
        // Subtotal domain
        if (!domain) {
            const datasetItemDomain = dataset.domains[0];
            const firstGroupBy = chart.dataSource._metaData.groupBy[0];
            domain = Domain.removeDomainLeaves(datasetItemDomain, [firstGroupBy]).toList();
        }
        return { name, domain };
    });
}

export function onGeoOdooChartItemClick(getters, chart) {
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem) => {
        const label = chartJsItem.element.feature.properties.name;
        const { datasets, labels } = chart.dataSource.getData();
        const index = labels.indexOf(label);
        if (index === -1) {
            return {};
        }
        const dataset = datasets[0];
        let name = labels[index];
        if (dataset.label) {
            name += ` / ${dataset.label}`;
        }
        return { name, domain: dataset.domains[index] };
    });
}

export function onSunburstOdooChartItemClick(getters, chart) {
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem, chartData, chartJSChart) => {
        const { datasetIndex, index } = chartJsItem;
        const rawItem = chartJSChart.data.datasets[datasetIndex].data[index];
        const domain = chart.dataSource.buildDomainFromGroupByLabels(rawItem.groups);
        return { name: rawItem.groups.join(" / "), domain: domain };
    });
}

export function onTreemapOdooChartItemClick(getters, chart) {
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem, chartData, chartJSChart) => {
        const { datasetIndex, index } = chartJsItem;
        const rawItem = chartJSChart.data.datasets[datasetIndex].data[index];
        const depth = rawItem.l;
        const groups = [];
        for (let i = 0; i <= depth; i++) {
            groups.push(rawItem._data[i]);
        }
        const domain = chart.dataSource.buildDomainFromGroupByLabels(groups);
        return { name: groups.join(" / "), domain: domain };
    });
}

function navigateInOdooMenuOnClick(getters, chart, getDomainFromChartItem) {
    return async (event, items, chartJSChart) => {
        const env = getters.getOdooEnv();
        const { datasets, labels } = chart.dataSource.getData();
        if (!items.length || !env || !datasets[items[0].datasetIndex]) {
            return;
        }
        if (event.type === "click" || isChartJSMiddleClick(event)) {
            event.native.preventDefault(); // Prevent other click actions
        } else {
            return;
        }
        const { name, domain } = getDomainFromChartItem(
            items[0],
            { datasets, labels },
            chartJSChart
        );
        if (!domain || !name) {
            return;
        }
        await navigateTo(
            env,
            chart.actionXmlId,
            {
                name,
                type: "ir.actions.act_window",
                res_model: chart.metaData.resModel,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain,
            },
            { viewType: "list", newWindow: isChartJSMiddleClick(event) }
        );
    };
}

export function onOdooChartItemHover() {
    return (event, items) => {
        if (items.length > 0) {
            event.native.target.style.cursor = "pointer";
        } else {
            event.native.target.style.cursor = "";
        }
    };
}

export function onGeoOdooChartItemHover() {
    return (event, items) => {
        if (!items.length) {
            event.native.target.style.cursor = "";
            return;
        }

        const item = items[0];
        const data = event.chart.data.datasets?.[item.datasetIndex]?.data?.[item.index];
        if (data?.value !== undefined) {
            event.native.target.style.cursor = "pointer";
        } else {
            event.native.target.style.cursor = "";
        }
    };
}

export async function navigateToOdooMenu(menu, actionService, notificationService, newWindow) {
    if (!menu) {
        throw new Error(`Cannot find any menu associated with the chart`);
    }
    if (!menu.actionID) {
        notificationService.add(
            _t(
                "The menu linked to this chart doesn't have an corresponding action. Please link the chart to another menu."
            ),
            { type: "danger" }
        );
        return;
    }
    await actionService.doAction(menu.actionID, { newWindow });
}

/**
 * Check if the even is a middle mouse click or ctrl+click
 *
 * ChartJS doesn't receive a click event when the user middle clicks on a chart, so we use the mouseup event instead.
 *
 */
export function isChartJSMiddleClick(event) {
    return (
        (event.type === "click" &&
            event.native.button === 0 &&
            (event.native.ctrlKey || event.native.metaKey)) ||
        (event.type === "mouseup" && event.native.button === 1)
    );
}
