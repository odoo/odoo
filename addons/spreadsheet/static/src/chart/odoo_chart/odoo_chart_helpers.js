import { navigateTo } from "@spreadsheet/actions/helpers";
import { Domain } from "@web/core/domain";

export function onOdooChartItemClick(getters, chart) {
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem) => {
        const { datasets, labels } = chart.dataSource.getData();
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
    return navigateInOdooMenuOnClick(getters, chart, (chartJsItem) => {
        const showSubtotals = chart.showSubTotals;
        const { datasets, labels } = chart.dataSource.getData();

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

function navigateInOdooMenuOnClick(getters, chart, getDomainFromChartItem) {
    return async (event, items) => {
        const env = getters.getOdooEnv();
        if (!items.length) {
            return;
        }
        if (!env) {
            return;
        }
        const { name, domain } = getDomainFromChartItem(items[0]);
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
            { viewType: "list" }
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
