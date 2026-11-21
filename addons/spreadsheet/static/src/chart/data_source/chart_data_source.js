import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { _t } from "@web/core/l10n/translation";
import { GraphModel as ChartModel } from "@web/views/graph/graph_model";
import { Domain } from "@web/core/domain";
import { range } from "@web/core/utils/numbers";
import { getCurrency } from "@web/core/currency";
import { computeFormatFromCurrency } from "@spreadsheet/currency/helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { helpers, constants } from "@odoo/o-spreadsheet";

const { toNumber } = helpers;
const { DEFAULT_LOCALE } = constants;

export const ODOO_CALENDAR_GRANULARITIES = {
    year: "year",
    quarter_number: "quarter",
    month_number: "month",
    day_of_week: "day",
    hour_number: "hour",
};

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
                calendarGroupBys: getCalendarGroupBys(chartDefinition),
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
        if (metaData.calendarGroupBys && this.getDateField()) {
            metaData.groupBy = [this._getCalendarDataSourceGroupBy()];
        }
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

    getLabelValues() {
        const { labels } = this.getData();
        if (!this._metaData.calendarGroupBys) {
            return labels;
        }
        const dateField = this.getDateField();
        if (!dateField || !this._model) {
            return labels.map(() => null);
        }
        const rawValues = {};
        for (const dataPoint of this._model.dataPoints) {
            const [groupValue] = Object.values(JSON.parse(dataPoint.identifier)[0]);
            rawValues[dataPoint.labels[0]] = groupValue && groupValue[0];
        }
        return labels.map((label) => {
            let value = rawValues[label];
            if (!value) {
                return null;
            }
            if (dateField.type === "datetime") {
                value = deserializeDateTime(value).toFormat("yyyy-MM-dd HH:mm:ss", {
                    numberingSystem: "latn",
                });
            }
            return toNumber(value, DEFAULT_LOCALE);
        });
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

    getDateField() {
        const fieldName = this._metaData.groupBy[0]?.split(":")[0];
        const field = fieldName && this._metaData.fields?.[fieldName];
        return ["date", "datetime"].includes(field?.type) ? field : undefined;
    }

    _getCalendarDataSourceGroupBy() {
        const { calendarGroupBys } = this._metaData;
        const dateField = this.getDateField();
        const grouping = Object.keys(ODOO_CALENDAR_GRANULARITIES).findLast((granularity) =>
            calendarGroupBys.includes(granularity)
        );
        let granularity = ODOO_CALENDAR_GRANULARITIES[grouping];
        if (granularity === "hour" && dateField.type === "date") {
            granularity = "day";
        }
        return `${dateField.name}:${granularity}`;
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

export function getCalendarGroupBys(chartDefinition) {
    if (chartDefinition.type !== "calendar") {
        return undefined;
    }
    return [
        chartDefinition.horizontalGroupBy ?? "day_of_week",
        chartDefinition.verticalGroupBy ?? "hour_number",
    ];
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
