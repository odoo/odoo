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
        this._startTime = performance.now();
        await this._model.load(this._searchParams);
        this._chartData = undefined;
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
        return this._getChartData();
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

    _getChartData() {
        if (this._chartData) {
            return this._chartData;
        }
        const { datasets, labels } = this._model.data;
        this._chartData = {
            datasets: datasets.map((ds) => ({
                ...ds,
                data: ds.data.map((d, index) => ({
                    value: d,
                    format: this._getCurrencyFormatForId(ds.currencyIds[index]),
                })),
            })),
            labels,
        };
        return this._chartData;
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

        for (const point of dataPoints) {
            labels.push({
                value: point.value,
                format: this._getCurrencyFormatForId(point.currencyId),
            });
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
