import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { ensureArray, sortBy } from "@web/core/utils/arrays";
import { KeepLast, Race } from "@web/core/utils/concurrency";
import { getAggregateCurrencyId, getCurrencyAggregateSpecs } from "@web/model/currency_aggregates";
import { addPropertyFieldDefs, Model } from "@web/model/model";
import { rankInterval } from "@web/search/utils/dates";
import { getGroupBy } from "@web/search/utils/group_by";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import { computeReportMeasures, processMeasure } from "@web/views/utils";

export const SEP = " / ";

export const SEQUENTIAL_TYPES = ["date", "datetime"];

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 */

export class GraphModel extends Model {
    /**
     * @override
     */
    setup(params) {
        // concurrency management
        this.keepLast = new KeepLast();
        this.race = new Race();
        const _fetchDataPoints = this._fetchDataPoints.bind(this);
        this._fetchDataPoints = (...args) => this.race.add(_fetchDataPoints(...args));

        this.initialGroupBy = null;

        this.metaData = params;
        this.data = null;
        this.searchParams = null;
        // This dataset will be added as a line plot on top of stacked bar chart.
        this.lineOverlayDataset = null;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {SearchParams} searchParams
     */
    async load(searchParams) {
        this.searchParams = searchParams;
        if (!this.initialGroupBy) {
            this.initialGroupBy = searchParams.context.graph_groupbys || this.metaData.groupBy; // = arch groupBy --> change that
        }
        const metaData = this._buildMetaData(this._getContextParams(searchParams.context));
        await addPropertyFieldDefs(
            this.orm,
            metaData.resModel,
            searchParams.context,
            metaData.fields,
            metaData.groupBy.map((gb) => gb.fieldName)
        );
        await this._fetchDataPoints(metaData);
    }

    /**
     * Several measures can only be displayed at once in pie mode: in the
     * other modes, only the first active measure is displayed.
     * @returns {string[]}
     */
    get displayedMeasures() {
        return this._getDisplayedMeasures(this.metaData);
    }

    /**
     * @override
     */
    hasData() {
        return this.dataPoints?.length > 0;
    }

    /**
     * Only supposed to be called to change one or several parameters among
     * "activeMeasures", "mode", "order", "stacked" and "cumulated".
     * @param {Object} params
     */
    async updateMetaData(params) {
        if ("activeMeasures" in params || "measure" in params) {
            if ("measure" in params && !("activeMeasures" in params)) {
                // backward compatibility with callers setting a single measure
                params.activeMeasures = ensureArray(params.measure);
                delete params.measure;
            }
            // build upon the metaData of a pending (re)load
            await this.race.getCurrentProm();
            const metaData = this._buildMetaData(params);
            await this._fetchDataPoints(metaData);
            this.useSampleModel = false; // can be removed
        } else {
            await this.race.getCurrentProm();
            const metaData = Object.assign({}, this.metaData, params);
            // only the displayed measures are fetched: fetch again if the new
            // mode displays measures that were not fetched (e.g. going back to
            // pie with several active measures)
            const fetchedMeasures = this.metaData.fetchedMeasures || [];
            const missingMeasures = this._getDisplayedMeasures(metaData).some(
                (measure) => !fetchedMeasures.includes(measure)
            );
            if (missingMeasures) {
                await this._fetchDataPoints(metaData);
            } else {
                this.metaData = metaData;
                this._prepareData();
            }
        }
        this.notify();
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean} true if the x-axis is grouped by a date or datetime field
     */
    hasDateXAxis() {
        const { fields, groupBy } = this.metaData;
        return ["date", "datetime"].includes(fields[groupBy[0]?.fieldName]?.type);
    }

    /**
     * @protected
     * @param {Object} [params={}]
     * @returns {Object}
     */
    _buildMetaData(params) {
        const { domain, context, groupBy } = this.searchParams;

        const metaData = Object.assign({}, this.metaData, { context });
        metaData.domain = domain;
        metaData.activeMeasures = ensureArray(
            metaData.activeMeasures || metaData.measure || "__count"
        );
        metaData.groupBy = groupBy.length ? groupBy : this.initialGroupBy;

        this._normalize(metaData);

        Object.assign(metaData, params);

        // sanitize the active measures: remove invalid or duplicated entries,
        // and make sure at least one measure remains active
        metaData.activeMeasures = metaData.activeMeasures
            .map((measure) => processMeasure(measure))
            .filter(
                (measure, index, measures) =>
                    (measure === "__count" || metaData.fields[measure]) &&
                    measures.indexOf(measure) === index
            );
        if (!metaData.activeMeasures.length) {
            metaData.activeMeasures = ["__count"];
        }
        // 'measure' is kept in sync with the first active measure for
        // compatibility (some code only handles a single measure)
        metaData.measure = metaData.activeMeasures[0];

        metaData.measures = computeReportMeasures(metaData.fields, metaData.fieldAttrs, [
            ...(metaData.viewMeasures || []),
            ...metaData.activeMeasures,
        ]);

        return metaData;
    }

    /**
     * Fetch the data points determined by the metaData. This function has
     * several side effects. It can alter this.metaData and set this.dataPoints.
     * @protected
     * @param {Object} metaData
     */
    async _fetchDataPoints(metaData) {
        [this.dataPoints] = await this.keepLast.add(this._loadDataPoints(metaData));
        this.metaData = metaData;
        this._prepareData();
    }

    /**
     * MetaData params from the "graph_" context keys. Only read at (re)load,
     * so that they do not override the user's changes (mode, measures...).
     * @protected
     * @param {Object} context
     * @returns {Object}
     */
    _getContextParams(context) {
        const params = {};
        if (context.graph_measure) {
            params.activeMeasures = ensureArray(processMeasure(context.graph_measure));
        }
        if (context.graph_mode) {
            params.mode = context.graph_mode;
        }
        const mode = params.mode || this.metaData.mode;
        if (mode !== "pie") {
            if ("graph_order" in context) {
                params.order = context.graph_order;
            }
            if ("graph_stacked" in context) {
                params.stacked = context.graph_stacked;
            }
            if (mode === "line" && "graph_cumulated" in context) {
                params.cumulated = context.graph_cumulated;
            } else if (mode === "bar" && "graph_all_dates" in context) {
                params.allDates = context.graph_all_dates;
            }
        }
        return params;
    }

    /**
     * Separates dataPoints coming from the read_group(s) into different
     * datasets. This function returns the parameters data and labels used
     * to produce the charts.
     * @protected
     * @param {Object[]} dataPoints
     * @returns {Object}
     */
    _getData(dataPoints) {
        const { mode } = this.metaData;

        // dataPoints --> labels
        const labels = [];
        const labelMap = {};
        for (const dataPt of dataPoints) {
            const x = dataPt.labels.slice(0, mode === "pie" ? undefined : 1);
            const trueLabel = x.length ? x.join(SEP) : _t("Total");
            const key = JSON.stringify(x);
            if (labelMap[key] === undefined) {
                labelMap[key] = labels.length;
                const label = x.length ? x.join(SEP) : _t("Total");
                labels.push(label);
            }
            dataPt.labelIndex = labelMap[key];
            dataPt.trueLabel = trueLabel;
        }

        // dataPoints + labels --> datasetsTmp --> datasets
        const datasetsTmp = new Map();
        for (const dataPt of dataPoints) {
            if (dataPt.count === 0 && this.metaData.groupBy.length > 1) {
                continue;
            }
            const { currencyId, domain, labelIndex, trueLabel, value, identifier, cumulatedStart } =
                dataPt;
            const datasetLabel = this._getDatasetLabel(dataPt);
            const datasetKey = mode === "pie" ? dataPt.measure : datasetLabel;
            let dataset = datasetsTmp.get(datasetKey);
            if (!dataset) {
                const dataLength = labels.length;
                dataset = {
                    data: new Array(dataLength).fill(0),
                    cumulatedStart,
                    trueLabels: labels.slice(0, dataLength),
                    domains: new Array(dataLength).fill([]),
                    label: datasetLabel,
                    identifiers: new Set(),
                    measure: dataPt.measure,
                    currencyIds: new Array(dataLength).fill(),
                };
                datasetsTmp.set(datasetKey, dataset);
            }
            dataset.data[labelIndex] = value;
            dataset.domains[labelIndex] = domain;
            dataset.trueLabels[labelIndex] = trueLabel;
            dataset.identifiers.add(identifier);
            dataset.currencyIds[labelIndex] = currencyId;
        }

        const datasets = [...datasetsTmp.values()];

        return { datasets, labels };
    }

    _getLineOverlayDataset() {
        const { stacked } = this.metaData;
        const datasets = this.data.datasets;
        let lineOverlayDataset = null;
        if (stacked && datasets.length > 1) {
            const label = _t("Sum");
            const data = [];
            const currencyIds = [];
            for (const dataset of datasets) {
                for (let i = 0; i < dataset.data.length; i++) {
                    data[i] = (data[i] || 0) + dataset.data[i];
                    currencyIds[i] = dataset.currencyIds[i] || currencyIds[i];
                }
            }
            lineOverlayDataset = {
                label,
                data,
                currencyIds,
                trueLabels: datasets[0].trueLabels,
            };
        }
        return lineOverlayDataset;
    }

    /**
     * Determines the display label of the dataset to which the data point belongs.
     * @protected
     * @param {Object} dataPoint
     * @returns {string}
     */
    _getDatasetLabel(dataPoint) {
        const { measures, mode } = this.metaData;
        const { labels } = dataPoint;
        if (mode === "pie") {
            // with several measures, the label of each dataset is its measure
            return this.displayedMeasures.length > 1 ? measures[dataPoint.measure].string : "";
        }
        return labels.slice(1).join(SEP) || measures[dataPoint.measure].string;
    }

    /**
     * @protected
     * @returns {string}
     */
    _getDefaultFilterLabel(gb) {
        return this.metaData.fields[gb?.fieldName]?.falsy_value_label || _t("None");
    }

    /**
     * @protected
     * @param {Object} metaData
     * @returns {string[]}
     */
    _getDisplayedMeasures({ activeMeasures, mode }) {
        return mode === "pie" ? activeMeasures : [activeMeasures[0]];
    }

    /**
     * Data points of the displayed measures only. Overrides of
     * _getProcessedDataPoints should start from these rather than from
     * this.dataPoints, which also contains the other active measures.
     * @protected
     * @returns {Object[]}
     */
    _getDisplayedDataPoints() {
        const displayedMeasures = this.displayedMeasures;
        return this.dataPoints.filter((dataPoint) => displayedMeasures.includes(dataPoint.measure));
    }

    /**
     * Eventually filters and sort data points.
     * @protected
     * @returns {Object[]}
     */
    _getProcessedDataPoints() {
        const { groupBy, mode, order } = this.metaData;
        const dataPoints = this._getDisplayedDataPoints();
        let processedDataPoints = [];
        if (mode === "line") {
            processedDataPoints = dataPoints.filter(
                (dataPoint) => dataPoint.labels[0] !== this._getDefaultFilterLabel(groupBy[0])
            );
        } else if (mode === "pie") {
            processedDataPoints = dataPoints.filter(
                (dataPoint) => dataPoint.value > 0 && dataPoint.count !== 0
            );
        } else if (this.metaData.allDates && this.hasDateXAxis()) {
            processedDataPoints = dataPoints;
        } else {
            processedDataPoints = dataPoints.filter((dataPoint) => dataPoint.count !== 0);
        }

        if (order !== null && mode !== "pie" && groupBy.length > 0) {
            // group data by their x-axis value, and then sort datapoints
            // based on the sum of values by group in ascending/descending order
            const groupedDataPoints = Object.create(null);
            for (const dataPt of processedDataPoints) {
                const key = dataPt.labels[0]; // = x-axis value under the current assumptions
                if (!groupedDataPoints[key]) {
                    groupedDataPoints[key] = [];
                }
                groupedDataPoints[key].push(dataPt);
            }
            const groups = Object.values(groupedDataPoints);
            const groupTotal = (group) => group.reduce((sum, dataPt) => sum + dataPt.value, 0);
            processedDataPoints = sortBy(groups, groupTotal, order.toLowerCase()).flat();
        }

        return processedDataPoints;
    }

    /**
     * Fetch and process graph data.  It is basically a(some) read_group(s)
     * with correct fields for each domain.  We have to do some light processing
     * to separate date groups in the field list, because they can be defined
     * with an aggregation function, such as my_date:week.
     * @protected
     * @param {Object} metaData
     * @returns {Array}
     */
    async _loadDataPoints(metaData) {
        const { domain, fields, groupBy, resModel, cumulatedStart } = metaData;
        // only fetch the displayed measures: the other active measures are kept
        // in the metaData (to be restored in pie mode) but fetching them would
        // only add aggregates to the read_group for nothing
        const fetchedMeasures = this._getDisplayedMeasures(metaData);
        metaData.fetchedMeasures = fetchedMeasures;
        metaData.allIntegersByMeasure = Object.fromEntries(
            fetchedMeasures.map((measure) => [measure, true])
        );
        const fieldName = groupBy[0]?.fieldName;
        const sequentialField =
            cumulatedStart && SEQUENTIAL_TYPES.includes(fields[fieldName]?.type) ? fieldName : null;
        const sequentialSpec = sequentialField && groupBy[0].spec;
        const aggregates = new Set(["__count"]);
        // aggregate spec of each fetched measure (plus the currency specs)
        const measureSpecs = {};
        for (const measure of fetchedMeasures) {
            if (measure === "__count") {
                measureSpecs[measure] = { aggregate: "__count" };
                continue;
            }
            let { aggregator, currency_field, type } = fields[measure];
            if (type === "many2one") {
                aggregator = "count_distinct";
            }
            if (aggregator === undefined) {
                throw new Error(
                    `No aggregate function has been provided for the measure '${measure}'`
                );
            }
            const spec = { aggregate: `${measure}:${aggregator}` };
            if (type === "monetary" && currency_field) {
                [spec.currencySpec, spec.convertedSpec] = getCurrencyAggregateSpecs(
                    fields[measure]
                );
                aggregates.add(spec.currencySpec);
                if (spec.convertedSpec) {
                    aggregates.add(spec.convertedSpec);
                }
            }
            aggregates.add(spec.aggregate);
            measureSpecs[measure] = spec;
        }
        const aggregateList = [...aggregates];

        const numbering = {}; // used to avoid ambiguity with many2one with values with same labels:
        // for instance [1, "ABC"] [3, "ABC"] should be distinguished.

        const groups = await this.orm.formattedReadGroup(
            resModel,
            domain,
            groupBy.map((gb) => gb.spec),
            aggregateList,
            {
                context: { fill_temporal: true, ...this.searchParams.context },
            }
        );
        let startGroups = false;
        if (
            cumulatedStart &&
            sequentialField &&
            groups.length &&
            domain.some((leaf) => leaf.length === 3 && leaf[0] == sequentialField)
        ) {
            const firstDate = groups[0][sequentialSpec][0];
            const newDomain = Domain.combine(
                [
                    new Domain([[sequentialField, "<", firstDate]]),
                    Domain.removeDomainLeaves(domain, [sequentialField]),
                ],
                "AND"
            ).toList();
            startGroups = await this.orm.formattedReadGroup(
                resModel,
                newDomain,
                groupBy.filter((gb) => gb.fieldName != sequentialField).map((gb) => gb.spec),
                aggregateList,
                {
                    context: { ...this.searchParams.context },
                }
            );
        }
        const dataPoints = [];
        const cumulatedStartValue = {};
        if (startGroups) {
            for (const group of startGroups) {
                const rawValues = [];
                for (const gb of groupBy.filter((gb) => gb.fieldName != sequentialField)) {
                    rawValues.push({ [gb.spec]: group[gb.spec] });
                }
                const startValues = {};
                for (const measure of fetchedMeasures) {
                    startValues[measure] = group[measureSpecs[measure].aggregate];
                }
                cumulatedStartValue[JSON.stringify(rawValues)] = startValues;
            }
        }
        const graphCurrencies = new Set();
        const defaultCurrency = user.activeCompany.currency_id;
        for (const group of groups) {
            const { __domain, __count } = group;
            const labels = [];
            const rawValues = [];
            for (const gb of groupBy) {
                let label;
                const val = group[gb.spec];
                rawValues.push({ [gb.spec]: val });
                const fieldName = gb.fieldName;
                const { type } = fields[fieldName];
                if (type === "boolean") {
                    label = `${val}`; // toUpperCase?
                } else if (type === "integer") {
                    label = val === false ? "0" : `${val}`;
                } else if (val === false) {
                    label = this._getDefaultFilterLabel(gb);
                } else if (["many2many", "many2one"].includes(type)) {
                    const [id, name] = val;
                    const key = JSON.stringify([fieldName, name]);
                    if (!numbering[key]) {
                        numbering[key] = {};
                    }
                    const numbers = numbering[key];
                    if (!numbers[id]) {
                        numbers[id] = Object.keys(numbers).length + 1;
                    }
                    const num = numbers[id];
                    label = num === 1 ? name : `${name} (${num})`;
                } else if (type === "selection") {
                    const selected = fields[fieldName].selection.find((s) => s[0] === val);
                    label = selected[1];
                } else if (["date", "datetime"].includes(type)) {
                    label = val[1];
                } else {
                    label = val;
                }
                labels.push(label);
            }

            const groupId = JSON.stringify(rawValues.slice(1));
            const identifier = JSON.stringify(rawValues);
            const startValues = cumulatedStartValue[groupId] || {};
            // a data point is created for each fetched measure of each group
            for (const measure of fetchedMeasures) {
                const spec = measureSpecs[measure];
                const value = group[spec.aggregate];
                const dataPoint = {
                    count: __count,
                    domain: __domain,
                    value,
                    labels,
                    identifier,
                    measure,
                    cumulatedStart: startValues[measure] || 0,
                };
                // There is a currency aggregate
                if (spec.currencySpec && __count) {
                    const currencies = group[spec.currencySpec];
                    dataPoint.currencyId = getAggregateCurrencyId(fields[measure], currencies);
                    if (spec.convertedSpec) {
                        dataPoint.convertedValue = group[spec.convertedSpec];
                        if (currencies.length > 1) {
                            dataPoint.value = dataPoint.convertedValue;
                        }
                    }
                    graphCurrencies.add(dataPoint.currencyId);
                }
                dataPoints.push(dataPoint);
            }
        }
        for (const dataPoint of dataPoints) {
            // points without a converted value keep their own currency
            if (graphCurrencies.size > 1 && dataPoint.convertedValue !== undefined) {
                dataPoint.currencyId = defaultCurrency;
                dataPoint.value = dataPoint.convertedValue;
            }
            if (!Number.isInteger(dataPoint.value)) {
                metaData.allIntegersByMeasure[dataPoint.measure] = false;
            }
            delete dataPoint.convertedValue;
        }
        // 'allIntegers' is kept in sync with the first active measure for
        // compatibility (some code only handles a single measure)
        metaData.allIntegers = metaData.allIntegersByMeasure[metaData.measure];
        return [dataPoints, graphCurrencies];
    }

    /**
     * Process metaData.groupBy in order to keep only the finest interval option for
     * elements based on date/datetime field (e.g. 'date:year'). This means that
     * 'week' is prefered to 'month'. The field stays at the place of its first occurence.
     * For instance,
     * ['foo', 'date:month', 'bar', 'date:week'] becomes ['foo', 'date:week', 'bar'].
     * @protected
     * @param {Object} metaData
     */
    _normalize(metaData) {
        const { fields } = metaData;
        const groupBy = [];
        for (const gb of metaData.groupBy) {
            let ngb = gb;
            if (typeof gb === "string") {
                ngb = getGroupBy(gb, fields);
            }
            groupBy.push(ngb);
        }

        const processedGroupBy = [];
        for (const gb of groupBy) {
            const { fieldName, interval } = gb;
            if (!fieldName.includes(".")) {
                const { groupable, type } = fields[fieldName];
                if (
                    // cf. _description_groupable in odoo/fields.py
                    !groupable ||
                    ["id", "__count"].includes(fieldName) ||
                    !GROUPABLE_TYPES.includes(type)
                ) {
                    continue;
                }
            }
            const index = processedGroupBy.findIndex((gb) => gb.fieldName === fieldName);
            if (index === -1) {
                processedGroupBy.push(gb);
            } else if (interval) {
                const registeredInterval = processedGroupBy[index].interval;
                if (rankInterval(registeredInterval) < rankInterval(interval)) {
                    processedGroupBy.splice(index, 1, gb);
                }
            }
        }
        metaData.groupBy = processedGroupBy;
    }

    /**
     * @protected
     */
    _prepareData() {
        const processedDataPoints = this._getProcessedDataPoints();
        this.data = this._getData(processedDataPoints);
        this.lineOverlayDataset = null;
        if (this.metaData.mode === "bar") {
            this.lineOverlayDataset = this._getLineOverlayDataset();
        }
    }
}
