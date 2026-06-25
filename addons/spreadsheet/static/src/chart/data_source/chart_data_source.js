import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { _t } from "@web/core/l10n/translation";
import { GraphModel as ChartModel } from "@web/views/graph/graph_model";
import { Domain } from "@web/core/domain";
import { range } from "@web/core/utils/numbers";
import { getCurrency } from "@web/core/currency";
import { computeFormatFromCurrency } from "@spreadsheet/currency/helpers";

export class ChartDataSource extends OdooViewsDataSource {
    /**
     * @override
     * @param {Object} services Services (see DataSource)
     */
    constructor(services, chartDefinition) {
        const dataSource = chartDefinition.dataSource;
        super(services, {
            ...dataSource,
            metaData: {
                ...dataSource.metaData,
                cumulatedStart: dataSource.cumulatedStart,
                mode: chartTypeToDataSourceMode(chartDefinition.type),
            },
        });
    }

    /**
     * @protected
     */
    async _load() {
        await super._load();
        const metaData = {
            fieldAttrs: {},
            ...this._metaData,
        };
        this._model = new ChartModel(
            {
                _t,
            },
            metaData,
            {
                orm: this._orm,
            }
        );
        await this._model.load(this._searchParams);
        this._hierarchicalData = undefined;
        this.labelToDomainMapping = undefined;
    }

    getData() {
        if (!this.isReady()) {
            this.load();
            return { datasets: [], labels: [] };
        }
        if (!this._isValid) {
            return { datasets: [], labels: [] };
        }
        const { datasets, labels } = this._model.data;

        // GraphModel normalizes all points in a dataset to the same currencyId,
        // so compute the format once from the first entry.
        const currencyId = datasets[0]?.currencyIds?.[0];
        const format = this._getCurrencyFormatForId(currencyId) ?? undefined;
        return {
            datasets: datasets.map((ds) => ({
                ...ds,
                data: ds.data.map((d) => ({ value: d, format })),
            })),
            labels,
        };
    }

    getHierarchicalData() {
        if (!this.isReady()) {
            this.load();
            return { datasets: [], labels: [] };
        }
        if (!this._isValid) {
            return { datasets: [], labels: [] };
        }
        return this._getHierarchicalData();
    }

    get source() {
        this._assertMetadataIsLoaded();
        const data = this._metaData;
        return {
            resModel: data.resModel,
            type: "graph",
            fields: [data.measure],
            groupby: data.groupBy,
            domain: this._searchParams.domain,
        };
    }

    changeChartType(newMode) {
        this._metaData.mode = newMode;
        this._model?.updateMetaData({ mode: newMode });
    }

    _getCurrencyFormatForId(currencyId) {
        const currency = getCurrency(currencyId);
        return computeFormatFromCurrency(currency);
    }

    _getHierarchicalData() {
        if (this._hierarchicalData && this.labelToDomainMapping) {
            return this._hierarchicalData;
        }
        const dataPoints = this._model.dataPoints;
        const groupBy = this._metaData.groupBy;
        const datasets = range(groupBy.length).map(() => ({
            data: [],
            domains: [],
            identifiers: [],
        }));
        const labels = new Array();
        const domainMapping = {};
        for (const gb of groupBy) {
            domainMapping[gb] = {};
        }

        // GraphModel normalizes all points to the same currencyId, so compute the format once.
        const format = this._getCurrencyFormatForId(dataPoints[0]?.currencyId);
        for (const point of dataPoints) {
            labels.push({ value: point.value, format });
            for (let i = 0; i < groupBy.length; i++) {
                datasets[i].data.push(point.labels[i]);
                datasets[i].identifiers.push(point.identifier);

                const label = point.labels[i];
                if (!domainMapping[groupBy[i]][label]) {
                    const gb = groupBy[i].split(":")[0];
                    domainMapping[groupBy[i]][label] = point.domain.filter((d) => d[0] === gb);
                }
            }
        }
        this._hierarchicalData = { datasets, labels };
        this.labelToDomainMapping = domainMapping;
        return this._hierarchicalData;
    }

    /**
     * Build a domain from the labels of the values of the groupBys.
     * Only works if getHierarchicalData was called before to build a mapping between groupBy labels and domains.
     */
    buildDomainFromGroupByLabels(groupByValuesLabels) {
        const domains = [this._searchParams.domain];
        for (let i = 0; i < groupByValuesLabels.length; i++) {
            const groupBy = this._metaData.groupBy[i];
            const label = groupByValuesLabels[i];
            if (this.labelToDomainMapping[groupBy]?.[label]) {
                domains.push(this.labelToDomainMapping[groupBy][label]);
            }
        }
        return Domain.and(domains).toList();
    }
}

export function chartTypeToDataSourceMode(chartType) {
    switch (chartType) {
        case "bar":
        case "line":
        case "pie":
            return chartType;
        default:
            return "bar";
    }
}
