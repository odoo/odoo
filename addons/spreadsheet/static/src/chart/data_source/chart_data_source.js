import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { _t } from "@web/core/l10n/translation";
import { GraphModel as ChartModel } from "@web/views/graph/graph_model";
import { Domain } from "@web/core/domain";

export class ChartDataSource extends OdooViewsDataSource {
    /**
     * @override
     * @param {Object} services Services (see DataSource)
     */
    constructor(services, params) {
        super(services, params);
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
        return this._model.data;
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

    changeChartType(newMode) {
        this._metaData.mode = newMode;
        this._model?.updateMetaData({ mode: newMode });
    }

    _getHierarchicalData() {
        if (this._hierarchicalData && this.labelToDomainMapping) {
            return this._hierarchicalData;
        }

        const dataPoints = this._model.dataPoints;
        const groupBy = this._metaData.groupBy;
        const datasets = new Array(groupBy.length).fill().map(() => ({ data: [], domains: [] }));
        const labels = new Array();
        const domainMapping = {};
        for (const gb of groupBy) {
            domainMapping[gb] = {};
        }

        for (const point of dataPoints) {
            labels.push(point.value.toString());
            for (let i = 0; i < groupBy.length; i++) {
                datasets[i].data.push(point.labels[i]);

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
        case "odoo_bar":
        case "odoo_line":
        case "odoo_pie":
            return chartType.replace("odoo_", "");
        default:
            return "bar";
    }
}
