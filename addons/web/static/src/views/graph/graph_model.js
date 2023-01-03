/** @odoo-module **/

import { sortBy } from "@web/core/utils/arrays";
import { KeepLast, Race } from "@web/core/utils/concurrency";
import { rankInterval } from "@web/search/utils/dates";
import { getGroupBy } from "@web/search/utils/group_by";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import { Model } from "@web/views/model";
import { computeReportMeasures, processMeasure } from "@web/views/utils";

export const SEP = " / ";

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 */

class DateClasses {
    // We view the param "array" as a matrix of values and undefined.
    // An equivalence class is formed of defined values of a column.
    // So nothing has to do with dates but we only use Dateclasses to manage
    // identification of dates.
    /**
     * @param {(any[])[]} array
     */
    constructor(array) {
        this.__referenceIndex = null;
        this.__array = array;
        for (let i = 0; i < this.__array.length; i++) {
            const arr = this.__array[i];
            if (arr.length && this.__referenceIndex === null) {
                this.__referenceIndex = i;
            }
        }
    }

    /**
     * @param {number} index
     * @param {any} o
     * @returns {string}
     */
    classLabel(index, o) {
        return `${this.__array[index].indexOf(o)}`;
    }

    /**
     * @param {string} classLabel
     * @returns {any[]}
     */
    classMembers(classLabel) {
        const classNumber = Number(classLabel);
        const classMembers = new Set();
        for (const arr of this.__array) {
            if (arr[classNumber] !== undefined) {
                classMembers.add(arr[classNumber]);
            }
        }
        return [...classMembers];
    }

    /**
     * @param {string} classLabel
     * @param {number} [index]
     * @returns {any}
     */
    representative(classLabel, index) {
        const classNumber = Number(classLabel);
        const i = index === undefined ? this.__referenceIndex : index;
        if (i === null) {
            return null;
        }
        return this.__array[i][classNumber];
    }

    /**
     * @param {number} index
     * @returns {number}
     */
    arrayLength(index) {
        return this.__array[index].length;
    }
}

export class GraphModel extends Model {
    /**
     * @override
     */
    setup(params) {
        // concurrency management
        this.keepLast = new KeepLast();
        this.race = new Race();
        const _fetchDataPoints = this._fetchDataPoints.bind(this);
        this._fetchDataPoints = (...args) => {
            return this.race.add(_fetchDataPoints(...args));
        };

        this.initialGroupBy = null;

        this.metaData = params;
        this.data = null;
        this.searchParams = null;
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
        const metaData = this._buildMetaData();
        return this._fetchDataPoints(metaData);
    }

    /**
     * @override
     */
    hasData() {
        return this.dataPoints.length > 0;
    }

    /**
     * Only supposed to be called to change one or several parameters among
     * "measure", "mode", "order", "stacked" and "cumulated".
     * @param {Object} params
     */
    async updateMetaData(params) {
        if ("measure" in params) {
            const metaData = this._buildMetaData(params);
            await this._fetchDataPoints(metaData);
        } else {
            await this.race.getCurrentProm();
            this.metaData = Object.assign({}, this.metaData, params);
            this._prepareData();
        }
        this.notify();
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * @protected
     * @param {Object} [params={}]
     * @returns {Object}
     */
    _buildMetaData(params) {
        const { comparison, domain, context, groupBy } = this.searchParams;

        const metaData = Object.assign({}, this.metaData, { context });
        if (comparison) {
            metaData.domains = comparison.domains;
            metaData.comparisonField = comparison.fieldName;
        } else {
            metaData.domains = [{ arrayRepr: domain, description: null }];
        }
        metaData.measure = context.graph_measure || metaData.measure;
        metaData.mode = context.graph_mode || metaData.mode;
        metaData.groupBy = groupBy.length ? groupBy : this.initialGroupBy;

        this._normalize(metaData);

        metaData.measures = computeReportMeasures(metaData.fields, metaData.fieldAttrs, [
            metaData.measure,
        ]);

        return Object.assign(metaData, params);
    }

    /**
     * Fetch the data points determined by the metaData. This function has
     * several side effects. It can alter this.metaData and set this.dataPoints.
     * @protected
     * @param {Object} metaData
     */
    async _fetchDataPoints(metaData) {
        this.dataPoints = await this.keepLast.add(this._loadDataPoints(metaData));
        this.metaData = metaData;
        this._prepareData();
    }

    /**
     * Separates dataPoints coming from the read_group(s) into different
     * datasets. This function returns the parameters data and labels used
     * to produce the charts.
     * @protected
     * @param {Object[]}
     * @returns {Object}
     */
    _getData(dataPoints) {
        const { comparisonField, groupBy, mode } = this.metaData;

        let identify = false;
        if (comparisonField && groupBy.length && groupBy[0].fieldName === comparisonField) {
            identify = true;
        }
        const dateClasses = identify ? this._getDateClasses(dataPoints) : null;

        // dataPoints --> labels
        let labels = [];
        const labelMap = {};
        for (const dataPt of dataPoints) {
            const x = dataPt.labels.slice(0, mode === "pie" ? undefined : 1);
            const trueLabel = x.length ? x.join(SEP) : this.env._t("Total");
            if (dateClasses) {
                x[0] = dateClasses.classLabel(dataPt.originIndex, x[0]);
            }
            const key = JSON.stringify(x);
            if (labelMap[key] === undefined) {
                labelMap[key] = labels.length;
                if (dateClasses) {
                    if (mode === "pie") {
                        x[0] = dateClasses.classMembers(x[0]).join(", ");
                    } else {
                        x[0] = dateClasses.representative(x[0]);
                    }
                }
                const label = x.length ? x.join(SEP) : this.env._t("Total");
                labels.push(label);
            }
            dataPt.labelIndex = labelMap[key];
            dataPt.trueLabel = trueLabel;
        }

        // dataPoints + labels --> datasetsTmp --> datasets
        const datasetsTmp = {};
        for (const dataPt of dataPoints) {
            const { domain, labelIndex, originIndex, trueLabel, value } = dataPt;
            const datasetLabel = this._getDatasetLabel(dataPt);
            if (!(datasetLabel in datasetsTmp)) {
                let dataLength = labels.length;
                if (mode !== "pie" && dateClasses) {
                    dataLength = dateClasses.arrayLength(originIndex);
                }
                datasetsTmp[datasetLabel] = {
                    data: new Array(dataLength).fill(0),
                    trueLabels: labels.slice(0, dataLength), // should be good // check this in case identify = true
                    domains: new Array(dataLength).fill([]),
                    label: datasetLabel,
                    originIndex: originIndex,
                };
            }
            datasetsTmp[datasetLabel].data[labelIndex] = value;
            datasetsTmp[datasetLabel].domains[labelIndex] = domain;
            datasetsTmp[datasetLabel].trueLabels[labelIndex] = trueLabel;
        }
        // sort by origin
        let datasets = sortBy(Object.values(datasetsTmp), "originIndex");

        if (mode === "pie") {
            // We kinda have a matrix. We remove the zero columns and rows. This is a global operation.
            // That's why it cannot be done before.
            datasets = datasets.filter((dataset) => dataset.data.some((v) => Boolean(v)));
            const labelsToKeepIndexes = {};
            labels.forEach((_, index) => {
                if (datasets.some((dataset) => Boolean(dataset.data[index]))) {
                    labelsToKeepIndexes[index] = true;
                }
            });
            labels = labels.filter((_, index) => labelsToKeepIndexes[index]);
            for (const dataset of datasets) {
                dataset.data = dataset.data.filter((_, index) => labelsToKeepIndexes[index]);
                dataset.domains = dataset.domains.filter((_, index) => labelsToKeepIndexes[index]);
                dataset.trueLabels = dataset.trueLabels.filter(
                    (_, index) => labelsToKeepIndexes[index]
                );
            }
        }

        return { datasets, labels };
    }

    /**
     * Determines the dataset to which the data point belongs.
     * @protected
     * @param {Object} dataPoint
     * @returns {string}
     */
    _getDatasetLabel(dataPoint) {
        const { measure, measures, domains, mode } = this.metaData;
        const { labels, originIndex } = dataPoint;
        if (mode === "pie") {
            return domains[originIndex].description || "";
        }
        // ([origin] + second to last groupBys) or measure
        let datasetLabel = labels.slice(1).join(SEP);
        if (domains.length > 1) {
            datasetLabel =
                domains[originIndex].description + (datasetLabel ? SEP + datasetLabel : "");
        }
        datasetLabel = datasetLabel || measures[measure].string;
        return datasetLabel;
    }

    /**
     * @protected
     * @param {Object[]} dataPoints
     * @returns {DateClasses}
     */
    _getDateClasses(dataPoints) {
        const { domains } = this.metaData;
        const dateSets = domains.map(() => new Set());
        for (const { labels, originIndex } of dataPoints) {
            const date = labels[0];
            dateSets[originIndex].add(date);
        }
        const arrays = dateSets.map((dateSet) => [...dateSet]);
        return new DateClasses(arrays);
    }

    /**
     * Eventually filters and sort data points.
     * @protected
     * @returns {Object[]}
     */
    _getProcessedDataPoints() {
        const { domains, groupBy, mode, order } = this.metaData;
        let processedDataPoints = [];
        if (mode === "line") {
            processedDataPoints = this.dataPoints.filter(
                (dataPoint) => dataPoint.labels[0] !== this.env._t("Undefined")
            );
        } else {
            processedDataPoints = this.dataPoints.filter((dataPoint) => dataPoint.count !== 0);
        }

        if (order !== null && mode !== "pie" && domains.length === 1 && groupBy.length > 0) {
            // group data by their x-axis value, and then sort datapoints
            // based on the sum of values by group in ascending/descending order
            const groupedDataPoints = {};
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
     * Determines whether the set of data points is good. If not, this.data will be (re)set to null
     * @protected
     * @param {Object[]}
     * @returns {boolean}
     */
    _isValidData(dataPoints) {
        const { mode } = this.metaData;
        let somePositive = false;
        let someNegative = false;
        if (mode === "pie") {
            for (const dataPt of dataPoints) {
                if (dataPt.value > 0) {
                    somePositive = true;
                } else if (dataPt.value < 0) {
                    someNegative = true;
                }
            }
            if (someNegative && somePositive) {
                return false;
            }
        }
        return true;
    }

    /**
     * Fetch and process graph data.  It is basically a(some) read_group(s)
     * with correct fields for each domain.  We have to do some light processing
     * to separate date groups in the field list, because they can be defined
     * with an aggregation function, such as my_date:week.
     * @protected
     * @param {Object} metaData
     * @returns {Object[]}
     */
    async _loadDataPoints(metaData) {
        const { measure, domains, fields, groupBy, resModel } = metaData;

        const measures = ["__count"];
        if (measure !== "__count") {
            let { group_operator, type } = fields[measure];
            if (type === "many2one") {
                group_operator = "count_distinct";
            }
            if (group_operator === undefined) {
                throw new Error(
                    `No aggregate function has been provided for the measure '${measure}'`
                );
            }
            measures.push(`${measure}:${group_operator}`);
        }

        const proms = [];
        const numbering = {}; // used to avoid ambiguity with many2one with values with same labels:
        // for instance [1, "ABC"] [3, "ABC"] should be distinguished.
        domains.forEach((domain, originIndex) => {
            proms.push(
                this.orm
                    .webReadGroup(
                        resModel,
                        domain.arrayRepr,
                        measures,
                        groupBy.map((gb) => gb.spec),
                        {
                            lazy: false, // what is this thing???
                            context: { fill_temporal: true, ...this.searchParams.context },
                        }
                    )
                    .then((data) => {
                        const dataPoints = [];
                        for (const group of data.groups) {
                            const { __domain, __count } = group;
                            const labels = [];

                            for (const gb of groupBy) {
                                let label;
                                const val = group[gb.spec];
                                const fieldName = gb.fieldName;
                                const { type } = fields[fieldName];
                                if (type === "boolean") {
                                    label = `${val}`; // toUpperCase?
                                } else if (val === false) {
                                    label = this.env._t("Undefined");
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
                                    const selected = fields[fieldName].selection.find(
                                        (s) => s[0] === val
                                    );
                                    label = selected[1];
                                } else {
                                    label = val;
                                }
                                labels.push(label);
                            }

                            let value = group[measure];
                            if (value instanceof Array) {
                                // case where measure is a many2one and is used as groupBy
                                value = 1;
                            }
                            if (!Number.isInteger(value)) {
                                metaData.allIntegers = false;
                            }
                            dataPoints.push({
                                count: __count,
                                domain: __domain,
                                value,
                                labels,
                                originIndex,
                            });
                        }
                        return dataPoints;
                    })
            );
        });
        const promResults = await Promise.all(proms);
        return promResults.flat();
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
            const { sortable, type, store } = fields[fieldName];
            if (
                // many2many is groupable precisely when it is stored (cf. groupable in odoo/fields.py)
                (type === "many2many" ? !store : !sortable) ||
                ["id", "__count"].includes(fieldName) ||
                !GROUPABLE_TYPES.includes(type)
            ) {
                continue;
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

        metaData.measure = processMeasure(metaData.measure);
    }

    /**
     * @protected
     */
    async _prepareData() {
        const processedDataPoints = this._getProcessedDataPoints();
        this.data = null;
        if (this._isValidData(processedDataPoints)) {
            this.data = this._getData(processedDataPoints);
        }
    }
}
