import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { groupBy, unique } from "@web/core/utils/arrays";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { pick } from "@web/core/utils/objects";
import { sprintf } from "@web/core/utils/strings";
import { Model } from "@web/model/model";
import { parseServerValue } from "@web/model/relational_model/utils";
import { formatFloatTime, formatPercentage } from "@web/views/fields/formatters";
import { getRangeFromDate, localStartOf } from "./gantt_helpers";

const { DateTime } = luxon;

/**
 * @typedef {luxon.DateTime} DateTime
 * @typedef {`[{${string}}]`} RowId
 * @typedef {import("./gantt_arch_parser").Scale} Scale
 * @typedef {import("./gantt_arch_parser").ScaleId} ScaleId
 *
 * @typedef ConsolidationParams
 * @property {string} excludeField
 * @property {string} field
 * @property {string} [maxField]
 * @property {string} [maxValue]
 *
 * @typedef Data
 * @property {Record<string, any>[]} records
 * @property {Row[]} rows
 *
 * @typedef Field
 * @property {string} name
 * @property {string} type
 * @property {[any, string][]} [selection]
 *
 * @typedef MetaData
 * @property {ConsolidationParams} consolidationParams
 * @property {string} dateStartField
 * @property {string} dateStopField
 * @property {string[]} decorationFields
 * @property {ScaleId} defaultScale
 * @property {string} dependencyField
 * @property {boolean} dynamicRange
 * @property {Record<string, Field>} fields
 * @property {DateTime} focusDate
 * @property {number | false} formViewId
 * @property {string[]} groupedBy
 * @property {Element | null} popoverTemplate
 * @property {string} resModel
 * @property {Scale} scale
 * @property {Scale[]} scales
 * @property {DateTime} startDate
 * @property {DateTime} stopDate
 *
 * @typedef ProgressBar
 * @property {number} value_formatted
 * @property {number} max_value_formatted
 * @property {number} ratio
 * @property {string} warning
 *
 * @typedef Row
 * @property {RowId} id
 * @property {boolean} consolidate
 * @property {boolean} fromServer
 * @property {string[]} groupedBy
 * @property {string} groupedByField
 * @property {number} groupLevel
 * @property {string} name
 * @property {number[]} recordIds
 * @property {ProgressBar} [progressBar]
 * @property {number | false} resId
 * @property {Row[]} [rows]
 */

function firstColumnBefore(date, unit) {
    return localStartOf(date, unit);
}

function firstColumnAfter(date, unit) {
    const start = localStartOf(date, unit);
    if (date.equals(start)) {
        return date;
    }
    return start.plus({ [unit]: 1 });
}

/**
 * @param {Record<string, Field>} fields
 * @param {Record<string, any>} values
 */
export function parseServerValues(fields, values) {
    /** @type {Record<string, any>} */
    const parsedValues = {};
    if (!values) {
        return parsedValues;
    }
    for (const fieldName in values) {
        const field = fields[fieldName];
        const value = values[fieldName];
        switch (field.type) {
            case "date": {
                parsedValues[fieldName] = value ? deserializeDate(value) : false;
                break;
            }
            case "datetime": {
                parsedValues[fieldName] = value ? deserializeDateTime(value) : false;
                break;
            }
            case "selection": {
                if (value === false) {
                    // process selection: convert false to 0, if 0 is a valid key
                    const hasKey0 = field.selection.some((option) => option[0] === 0);
                    parsedValues[fieldName] = hasKey0 ? 0 : value;
                } else {
                    parsedValues[fieldName] = value;
                }
                break;
            }
            case "html": {
                parsedValues[fieldName] = parseServerValue(field, value);
                break;
            }
            case "many2one": {
                parsedValues[fieldName] = value ? [value.id, value.display_name] : false;
                break;
            }
            default: {
                parsedValues[fieldName] = value;
            }
        }
    }
    return parsedValues;
}

export class GanttModel extends Model {
    static services = ["notification"];

    setup(params, services) {
        this.notification = services.notification;

        /** @type {Data} */
        this.data = {};
        /** @type {MetaData} */
        this.metaData = params.metaData;
        this.displayParams = params.displayParams;

        this.searchParams = null;

        /** @type {Set<RowId>} */
        this.closedRows = new Set();

        // concurrency management
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();
        /** @type {MetaData | null} */
        this._nextMetaData = null;
    }

    /**
     * @param {SearchParams} searchParams
     */
    async load(searchParams) {
        this.searchParams = searchParams;

        const metaData = this._buildMetaData();

        const params = {
            groupedBy: this._getGroupedBy(metaData, searchParams),
            pagerOffset: 0,
        };

        if (!metaData.scale || !metaData.startDate || !metaData.stopDate) {
            Object.assign(
                params,
                this._getInitialRangeParams(this._buildMetaData(params), searchParams)
            );
        }

        await this._fetchData(this._buildMetaData(params));
    }

    //-------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    collapseRows() {
        const collapse = (rows) => {
            for (const row of rows) {
                this.closedRows.add(row.id);
                if (row.rows) {
                    collapse(row.rows);
                }
            }
        };
        collapse(this.data.rows);
        this.notify();
    }

    /**
     * Create a copy of a task with defaults determined by schedule.
     *
     * @param {number} id
     * @param {Record<string, any>} schedule
     * @param {(result: any) => any} [callback]
     */
    copy(id, schedule, callback) {
        const { resModel } = this.metaData;
        const { context } = this.searchParams;
        const data = this._scheduleToData(schedule);
        return this.mutex.exec(async () => {
            const result = await this.orm.call(resModel, "copy", [[id]], {
                context,
                default: data,
            });
            if (callback) {
                callback(result[0]);
            }
            this.fetchData();
        });
    }

    /**
     * Adds a dependency between masterId and slaveId (slaveId depends
     * on masterId).
     *
     * @param {number} masterId
     * @param {number} slaveId
     */
    async createDependency(masterId, slaveId) {
        const { dependencyField, resModel } = this.metaData;
        const writeCommand = {
            [dependencyField]: [x2ManyCommands.link(masterId)],
        };
        await this.mutex.exec(() => this.orm.write(resModel, [slaveId], writeCommand));
        await this.fetchData();
    }

    dateStartFieldIsDate(metaData = this.metaData) {
        return metaData?.fields[metaData.dateStartField].type === "date";
    }

    dateStopFieldIsDate(metaData = this.metaData) {
        return metaData?.fields[metaData.dateStopField].type === "date";
    }

    expandRows() {
        this.closedRows.clear();
        this.notify();
    }

    async fetchData(params) {
        await this._fetchData(this._buildMetaData(params));
        this.useSampleModel = false;
        this.notify();
    }

    /**
     * @param {Object} params
     * @param {RowId} [params.rowId]
     * @param {DateTime} [params.start]
     * @param {DateTime} [params.stop]
     * @param {boolean} [params.withDefault]
     * @returns {Record<string, any>}
     */
    getDialogContext(params) {
        /** @type {Record<string, any>} */
        const context = { ...this.getSchedule(params) };

        if (params.withDefault) {
            for (const k in context) {
                context[sprintf("default_%s", k)] = context[k];
            }
        }

        return Object.assign({}, this.searchParams.context, context);
    }

    /**
     * @param {Object} params
     * @param {RowId} [params.rowId]
     * @param {DateTime} [params.start]
     * @param {DateTime} [params.stop]
     * @returns {Record<string, any>}
     */
    getSchedule({ rowId, start, stop } = {}) {
        const { dateStartField, dateStopField, fields, groupedBy } = this.metaData;

        /** @type {Record<string, any>} */
        const schedule = {};

        if (start) {
            schedule[dateStartField] = this.dateStartFieldIsDate()
                ? serializeDate(start)
                : serializeDateTime(start);
        }
        if (stop && dateStartField !== dateStopField) {
            schedule[dateStopField] = this.dateStopFieldIsDate()
                ? serializeDate(stop)
                : serializeDateTime(stop);
        }
        if (rowId) {
            const group = Object.assign({}, ...JSON.parse(rowId));
            for (const fieldName of groupedBy) {
                if (fieldName in group) {
                    const value = group[fieldName];
                    if (Array.isArray(value)) {
                        const { type } = fields[fieldName];
                        schedule[fieldName] = type === "many2many" ? [value[0]] : value[0];
                    } else {
                        schedule[fieldName] = value;
                    }
                }
            }
        }

        return schedule;
    }

    /**
     * @override
     * @returns {boolean}
     */
    hasData() {
        return Boolean(this.data.records.length);
    }

    /**
     * @param {RowId} rowId
     * @returns {boolean}
     */
    isClosed(rowId) {
        return this.closedRows.has(rowId);
    }

    /**
     * Removes the dependency between masterId and slaveId (slaveId is no
     * more dependent on masterId).
     *
     * @param {number} masterId
     * @param {number} slaveId
     */
    async removeDependency(masterId, slaveId) {
        const { dependencyField, resModel } = this.metaData;
        const writeCommand = {
            [dependencyField]: [x2ManyCommands.unlink(masterId)],
        };
        await this.mutex.exec(() => this.orm.write(resModel, [slaveId], writeCommand));
        await this.fetchData();
    }

    /**
     * Removes from 'data' the fields holding the same value as the records targetted
     * by 'ids'.
     *
     * @template {Record<string, any>} T
     * @param {T} data
     * @param {number[]} ids
     * @returns {Partial<T>}
     */
    removeRedundantData(data, ids) {
        const records = this.data.records.filter((rec) => ids.includes(rec.id));
        if (!records.length) {
            return data;
        }

        /**
         *
         * @param {Record<string, any>} record
         * @param {Field} field
         */
        const isSameValue = (record, { name, type }) => {
            const recordValue = record[name];
            let newValue = data[name];
            if (Array.isArray(newValue)) {
                [newValue] = newValue;
            }
            if (Array.isArray(recordValue)) {
                if (type === "many2many") {
                    return recordValue.includes(newValue);
                } else {
                    return recordValue[0] === newValue;
                }
            } else if (type === "date") {
                return serializeDate(recordValue) === newValue;
            } else if (type === "datetime") {
                return serializeDateTime(recordValue) === newValue;
            } else {
                return recordValue === newValue;
            }
        };

        /** @type {Partial<T>} */
        const trimmed = { ...data };

        for (const fieldName in data) {
            const field = this.metaData.fields[fieldName];
            if (records.every((rec) => isSameValue(rec, field))) {
                // All the records already have the given value.
                delete trimmed[fieldName];
            }
        }

        return trimmed;
    }

    /**
     * Reschedule a task to the given schedule.
     *
     * @param {number | number[]} ids
     * @param {Record<string, any>} schedule
     * @param {(result: any) => any} [callback]
     */
    async reschedule(ids, schedule, callback) {
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const allData = this._scheduleToData(schedule);
        const data = this.removeRedundantData(allData, ids);
        const context = this._getRescheduleContext();
        return this.mutex.exec(async () => {
            try {
                const result = await this._reschedule(ids, data, context);
                if (callback) {
                    await callback(result);
                }
            } finally {
                this.fetchData();
            }
        });
    }

    async _reschedule(ids, data, context) {
        return this.orm.write(this.metaData.resModel, ids, data, {
            context,
        });
    }

    toggleHighlightPlannedFilter(ids) {}

    /**
     * Reschedule masterId or slaveId according to the direction
     *
     * @param {"forward" | "backward"} direction
     * @param {number} masterId
     * @param {number} slaveId
     * @returns {Promise<any>}
     */
    async rescheduleAccordingToDependency(
        direction,
        masterId,
        slaveId,
        rescheduleAccordingToDependencyCallback
    ) {
        const {
            dateStartField,
            dateStopField,
            dependencyField,
            dependencyInvertedField,
            resModel,
        } = this.metaData;

        return await this.mutex.exec(async () => {
            try {
                const result = await this.orm.call(resModel, "web_gantt_reschedule", [
                    direction,
                    masterId,
                    slaveId,
                    dependencyField,
                    dependencyInvertedField,
                    dateStartField,
                    dateStopField,
                ]);
                if (rescheduleAccordingToDependencyCallback) {
                    await rescheduleAccordingToDependencyCallback(result);
                }
            } finally {
                this.fetchData();
            }
        });
    }

    /**
     * @param {string} rowId
     */
    toggleRow(rowId) {
        if (this.isClosed(rowId)) {
            this.closedRows.delete(rowId);
        } else {
            this.closedRows.add(rowId);
        }
        this.notify();
    }

    async toggleDisplayMode() {
        this.displayParams.displayMode =
            this.displayParams.displayMode === "dense" ? "sparse" : "dense";
        this.notify();
    }

    async updatePagerParams({ limit, offset }) {
        await this.fetchData({ pagerLimit: limit, pagerOffset: offset });
    }

    //-------------------------------------------------------------------------
    // Protected
    //-------------------------------------------------------------------------

    /**
     * Return a copy of this.metaData or of the last copy, extended with optional
     * params. This is useful for async methods that need to modify this.metaData,
     * but it can't be done in place directly for the model to be concurrency
     * proof (so they work on a copy and commit it at the end).
     *
     * @protected
     * @param {Object} params
     * @param {DateTime} [params.focusDate]
     * @param {DateTime} [params.startDate]
     * @param {DateTime} [params.stopDate]
     * @param {string[]} [params.groupedBy]
     * @param {ScaleId} [params.scaleId]
     * @returns {MetaData}
     */
    _buildMetaData(params = {}) {
        this._nextMetaData = { ...(this._nextMetaData || this.metaData) };

        if (params.groupedBy) {
            this._nextMetaData.groupedBy = params.groupedBy;
        }
        if (params.scaleId) {
            browser.localStorage.setItem(this._getLocalStorageKey(), params.scaleId);
            this._nextMetaData.scale = { ...this._nextMetaData.scales[params.scaleId] };
        }
        if (params.focusDate) {
            this._nextMetaData.focusDate = params.focusDate;
        }
        if (params.startDate) {
            this._nextMetaData.startDate = params.startDate;
        }
        if (params.stopDate) {
            this._nextMetaData.stopDate = params.stopDate;
        }
        if (params.rangeId) {
            this._nextMetaData.rangeId = params.rangeId;
        }

        if ("pagerLimit" in params) {
            this._nextMetaData.pagerLimit = params.pagerLimit;
        }
        if ("pagerOffset" in params) {
            this._nextMetaData.pagerOffset = params.pagerOffset;
        }

        if ("scaleId" in params || "startDate" in params || "stopDate" in params) {
            // we assume that scale, startDate, and stopDate are already set in this._nextMetaData

            let exchange = false;
            if (this._nextMetaData.startDate > this._nextMetaData.stopDate) {
                exchange = true;
                const temp = this._nextMetaData.startDate;
                this._nextMetaData.startDate = this._nextMetaData.stopDate;
                this._nextMetaData.stopDate = temp;
            }
            const { interval } = this._nextMetaData.scale;

            const rightLimit = this._nextMetaData.startDate.plus({ year: 10, day: -1 });
            if (this._nextMetaData.stopDate > rightLimit) {
                if (exchange) {
                    this._nextMetaData.startDate = this._nextMetaData.stopDate.minus({
                        year: 10,
                        day: -1,
                    });
                } else {
                    this._nextMetaData.stopDate = this._nextMetaData.startDate.plus({
                        year: 10,
                        day: -1,
                    });
                }
            }
            this._nextMetaData.globalStart = firstColumnBefore(
                this._nextMetaData.startDate,
                interval
            );
            this._nextMetaData.globalStop = firstColumnAfter(
                this._nextMetaData.stopDate.plus({ day: 1 }),
                interval
            );

            if (params.currentFocusDate) {
                this._nextMetaData.focusDate = params.currentFocusDate;
                if (this._nextMetaData.focusDate < this._nextMetaData.startDate) {
                    this._nextMetaData.focusDate = this._nextMetaData.startDate;
                } else if (this._nextMetaData.stopDate < this._nextMetaData.focusDate) {
                    this._nextMetaData.focusDate = this._nextMetaData.stopDate;
                }
            }
        }

        return this._nextMetaData;
    }

    /**
     * Fetches records to display (and groups if necessary).
     *
     * @protected
     * @param {MetaData} metaData
     * @param {Object} [additionalContext]
     */
    async _fetchData(metaData, additionalContext) {
        const { globalStart, globalStop, groupedBy, pagerLimit, pagerOffset, resModel, scale } =
            metaData;
        const context = {
            ...this.searchParams.context,
            group_by: groupedBy,
            ...additionalContext,
        };
        const domain = this._getDomain(metaData);
        const fields = this._getFields(metaData);
        const specification = {};
        for (const fieldName of fields) {
            specification[fieldName] = {};
            if (metaData.fields[fieldName].type === "many2one") {
                specification[fieldName].fields = { display_name: {} };
            }
        }

        const { length, groups, records, progress_bars, unavailabilities } =
            await this.keepLast.add(
                this.orm.call(resModel, "get_gantt_data", [], {
                    domain,
                    groupby: groupedBy,
                    read_specification: specification,
                    scale: scale.unit,
                    start_date: serializeDateTime(globalStart),
                    stop_date: serializeDateTime(globalStop),
                    unavailability_fields: this._getUnavailabilityFields(metaData),
                    progress_bar_fields: this._getProgressBarFields(metaData),
                    context,
                    limit: pagerLimit,
                    offset: pagerOffset,
                })
            );

        groups.forEach((g) => (g.fromServer = true));

        const data = { count: length };

        data.records = this._parseServerData(metaData, records);
        data.rows = this._generateRows(metaData, {
            groupedBy,
            groups,
            parentGroup: [],
        });
        data.unavailabilities = this._processUnavailabilities(unavailabilities);
        data.progressBars = this._processProgressBars(progress_bars);

        await this.keepLast.add(this._fetchDataPostProcess(metaData, data));

        this.data = data;
        this.metaData = metaData;
        this._nextMetaData = null;
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {Data} data
     */
    async _fetchDataPostProcess(metaData, data) {}

    /**
     * Remove date in groupedBy field
     *
     * @protected
     * @param {MetaData} metaData
     * @param {string[]} groupedBy
     * @returns {string[]}
     */
    _filterDateIngroupedBy(metaData, groupedBy) {
        return groupedBy.filter((gb) => {
            const [fieldName] = gb.split(":");
            const { type } = metaData.fields[fieldName];
            return !["date", "datetime"].includes(type);
        });
    }

    /**
     * @protected
     * @param {number} floatVal
     * @param {string}
     */
    _formatTime(floatVal) {
        const timeStr = formatFloatTime(floatVal, { noLeadingZeroHour: true });
        const [hourStr, minuteStr] = timeStr.split(":");
        const hour = parseInt(hourStr, 10);
        const minute = parseInt(minuteStr, 10);
        return minute ? _t("%(hour)sh%(minute)s", { hour, minute }) : _t("%sh", hour);
    }

    /**
     * Process groups to generate a recursive structure according
     * to groupedBy fields. Note that there might be empty groups (filled by
     * read_goup with group_expand) that also need to be processed.
     *
     * @protected
     * @param {MetaData} metaData
     * @param {Object} params
     * @param {Object[]} params.groups
     * @param {string[]} params.groupedBy
     * @param {Object[]} params.parentGroup
     * @returns {Row[]}
     */
    _generateRows(metaData, params) {
        const groupedBy = params.groupedBy;
        const groups = params.groups;
        const groupLevel = metaData.groupedBy.length - groupedBy.length;
        const parentGroup = params.parentGroup;

        if (!groupedBy.length || !groups.length) {
            const recordIds = [];
            for (const g of groups) {
                recordIds.push(...(g.__record_ids || []));
            }
            const part = parentGroup.at(-1);
            const [[parentGroupedField, value]] = part ? Object.entries(part) : [[]];
            return [
                {
                    groupLevel,
                    id: JSON.stringify([...parentGroup, {}]),
                    name: "",
                    recordIds: unique(recordIds),
                    parentGroupedField,
                    parentResId: Array.isArray(value) ? value[0] : value,
                    __extra__: true,
                },
            ];
        }

        /** @type {Row[]} */
        const rows = [];

        // Some groups might be empty (thanks to expand_groups), so we can't
        // simply group the data, we need to keep all returned groups
        const groupedByField = groupedBy[0];
        const currentLevelGroups = groupBy(groups, (g) => {
            if (g[groupedByField] === undefined) {
                // we want to group the groups with undefined values for groupedByField with the ones
                // with false value for the same field.
                // we also want to be sure that stringification keeps groupedByField:
                // JSON.stringify({ key: undefined }) === "{}"
                // see construction of id below.
                g[groupedByField] = false;
            }
            return g[groupedByField];
        });
        const { maxField } = metaData.consolidationParams;
        const consolidate = groupLevel === 0 && groupedByField === maxField;
        const generateSubRow = maxField ? true : groupedBy.length > 1;
        for (const key in currentLevelGroups) {
            const subGroups = currentLevelGroups[key];
            const value = subGroups[0][groupedByField];
            const part = {};
            part[groupedByField] = value;
            const fakeGroup = [...parentGroup, part];
            const id = JSON.stringify(fakeGroup);
            const resId = Array.isArray(value) ? value[0] : value; // not really a resId
            const fromServer = subGroups.some((g) => g.fromServer);
            const recordIds = [];
            for (const g of subGroups) {
                recordIds.push(...(g.__record_ids || []));
            }
            const row = {
                consolidate,
                fromServer,
                groupedBy,
                groupedByField,
                groupLevel,
                id,
                name: this._getRowName(metaData, groupedByField, value),
                resId, // not really a resId
                recordIds: unique(recordIds),
            };
            if (generateSubRow) {
                row.rows = this._generateRows(metaData, {
                    ...params,
                    groupedBy: groupedBy.slice(1),
                    groups: subGroups,
                    parentGroup: fakeGroup,
                });
            }
            if (resId === false) {
                rows.unshift(row);
            } else {
                rows.push(row);
            }
        }

        return rows;
    }

    /**
     * Get domain of records to display in the gantt view.
     *
     * @protected
     * @param {MetaData} metaData
     * @returns {any[]}
     */
    _getDomain(metaData) {
        const { dateStartField, dateStopField, globalStart, globalStop } = metaData;
        const domain = Domain.and([
            this.searchParams.domain,
            [
                "&",
                [
                    dateStartField,
                    "<",
                    this.dateStopFieldIsDate(metaData)
                        ? serializeDate(globalStop)
                        : serializeDateTime(globalStop),
                ],
                [
                    dateStopField,
                    this.dateStartFieldIsDate(metaData) ? ">=" : ">",
                    this.dateStartFieldIsDate(metaData)
                        ? serializeDate(globalStart)
                        : serializeDateTime(globalStart),
                ],
            ],
        ]);
        return domain.toList();
    }

    /**
     * Format field value to display purpose.
     *
     * @protected
     * @param {any} value
     * @param {Object} field
     * @returns {string} formatted field value
     */
    _getFieldFormattedValue(value, field) {
        if (field.type === "boolean") {
            return value ? "True" : "False";
        } else if (!value) {
            return _t("Undefined %s", field.string);
        } else if (field.type === "many2many") {
            return value[1];
        }
        const formatter = registry.category("formatters").get(field.type);
        return formatter(value, field);
    }

    /**
     * Get all the fields needed.
     *
     * @protected
     * @param {MetaData} metaData
     * @returns {string[]}
     */
    _getFields(metaData) {
        const fields = new Set([
            "display_name",
            metaData.dateStartField,
            metaData.dateStopField,
            ...metaData.groupedBy,
            ...metaData.decorationFields,
        ]);
        if (metaData.colorField) {
            fields.add(metaData.colorField);
        }
        if (metaData.consolidationParams.field) {
            fields.add(metaData.consolidationParams.field);
        }
        if (metaData.consolidationParams.excludeField) {
            fields.add(metaData.consolidationParams.excludeField);
        }
        if (metaData.dependencyField) {
            fields.add(metaData.dependencyField);
        }
        if (metaData.progressField) {
            fields.add(metaData.progressField);
        }
        return [...fields];
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {{ groupBy: string[] }} searchParams
     * @returns {string[]}
     */
    _getGroupedBy(metaData, searchParams) {
        let groupedBy = [...searchParams.groupBy];
        groupedBy = groupedBy.filter((gb) => {
            const [fieldName] = gb.split(".");
            const field = metaData.fields[fieldName];
            return field?.type !== "properties";
        });
        groupedBy = this._filterDateIngroupedBy(metaData, groupedBy);
        if (!groupedBy.length) {
            groupedBy = metaData.defaultGroupBy;
        }
        return groupedBy;
    }

    _getDefaultFocusDate(metaData, searchParams, scaleId) {
        const { context } = searchParams;
        let focusDate =
            "initialDate" in context ? deserializeDateTime(context.initialDate) : DateTime.local();
        focusDate = focusDate.startOf("day");
        if (metaData.offset) {
            const { unit } = metaData.scales[scaleId];
            focusDate = focusDate.plus({ [unit]: metaData.offset });
        }
        return focusDate;
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {{ context: Record<string, any> }} searchParams
     * @returns {{ focusDate: DateTime, scaleId: ScaleId, startDate: DateTime, stopDate: DateTime }}
     */
    _getInitialRangeParams(metaData, searchParams) {
        const { context } = searchParams;
        const localScaleId = this._getScaleIdFromLocalStorage(metaData);
        /** @type {ScaleId} */
        const scaleId = localScaleId || context.default_scale || metaData.defaultScale;
        const { defaultRange } = metaData.scales[scaleId];

        const rangeId =
            context.default_range in metaData.ranges
                ? context.range_type
                : metaData.defaultRange || "custom";
        let focusDate;
        if (rangeId in metaData.ranges) {
            focusDate = this._getDefaultFocusDate(metaData, searchParams, scaleId);
            return { scaleId, ...getRangeFromDate(rangeId, focusDate) };
        }
        let startDate = context.default_start_date && deserializeDate(context.default_start_date);
        let stopDate = context.default_stop_date && deserializeDate(context.default_stop_date);
        if (!startDate && !stopDate) {
            /** @type {DateTime} */
            focusDate = this._getDefaultFocusDate(metaData, searchParams, scaleId);
            startDate = firstColumnBefore(focusDate, defaultRange.unit);
            stopDate = startDate
                .plus({ [defaultRange.unit]: defaultRange.count })
                .minus({ day: 1 });
        } else if (startDate && !stopDate) {
            const column = firstColumnBefore(startDate, defaultRange.unit);
            focusDate = startDate;
            stopDate = column.plus({ [defaultRange.unit]: defaultRange.count }).minus({ day: 1 });
        } else if (!startDate && stopDate) {
            const column = firstColumnAfter(stopDate, defaultRange.unit);
            focusDate = stopDate;
            startDate = column.minus({ [defaultRange.unit]: defaultRange.count });
        } else {
            focusDate = DateTime.local();
            if (focusDate < startDate) {
                focusDate = startDate;
            } else if (focusDate > stopDate) {
                focusDate = stopDate;
            }
        }

        return { focusDate, scaleId, startDate, stopDate, rangeId };
    }

    _getLocalStorageKey() {
        return `scaleOf-viewId-${this.env.config.viewId}`;
    }

    _getProgressBarFields(metaData) {
        if (metaData.progressBarFields && !this.orm.isSample) {
            return metaData.progressBarFields.filter(
                (fieldName) =>
                    metaData.groupedBy.includes(fieldName) &&
                    ["many2many", "many2one"].includes(metaData.fields[fieldName]?.type)
            );
        }
        return [];
    }

    _getRescheduleContext() {
        return { ...this.searchParams.context };
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {string} groupedByField
     * @param {any} value
     * @returns {string}
     */
    _getRowName(metaData, groupedByField, value) {
        const field = metaData.fields[groupedByField];
        return this._getFieldFormattedValue(value, field);
    }

    _getScaleIdFromLocalStorage(metaData) {
        const { scales } = metaData;
        const localScaleId = browser.localStorage.getItem(this._getLocalStorageKey());
        return localScaleId in scales ? localScaleId : null;
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @returns {string[]}
     */
    _getUnavailabilityFields(metaData) {
        if (metaData.displayUnavailability && !this.orm.isSample && metaData.groupedBy.length) {
            const lastGroupBy = metaData.groupedBy.at(-1);
            const { type } = metaData.fields[lastGroupBy] || {};
            if (["many2many", "many2one"].includes(type)) {
                return [lastGroupBy];
            }
        }
        return [];
    }

    /**
     * @protected
     * @param {MetaData} metaData
     * @param {Record<string, any>[]} records the server records to parse
     * @returns {Record<string, any>[]}
     */
    _parseServerData(metaData, records) {
        const { dateStartField, dateStopField, fields, globalStart, globalStop } = metaData;
        /** @type {Record<string, any>[]} */
        const parsedRecords = [];
        for (const record of records) {
            const parsedRecord = parseServerValues(fields, record);
            const dateStart = parsedRecord[dateStartField];
            const dateStop = parsedRecord[dateStopField];
            if (this.orm.isSample) {
                // In sample mode, we want enough data to be displayed, so we
                // swap the dates as the records are randomly generated anyway.
                if (dateStart > dateStop) {
                    parsedRecord[dateStartField] = dateStop;
                    parsedRecord[dateStopField] = dateStart;
                }
                // Record could also be outside the displayed range since the
                // sample server doesn't take the domain into account
                if (parsedRecord[dateStopField] < globalStart) {
                    parsedRecord[dateStopField] = globalStart;
                }
                if (parsedRecord[dateStartField] > globalStop) {
                    parsedRecord[dateStartField] = globalStop;
                }
                parsedRecords.push(parsedRecord);
            } else if (dateStart <= dateStop) {
                parsedRecords.push(parsedRecord);
            }
        }
        return parsedRecords;
    }

    _processProgressBar(progressBar, warning) {
        const processedProgressBar = {
            ...progressBar,
            value_formatted: this._formatTime(progressBar.value),
            max_value_formatted: this._formatTime(progressBar.max_value),
            ratio: progressBar.max_value ? (progressBar.value / progressBar.max_value) * 100 : 0,
            warning,
        };
        if (processedProgressBar?.max_value) {
            processedProgressBar.ratio_formatted = formatPercentage(
                processedProgressBar.ratio / 100
            );
        }
        return processedProgressBar;
    }

    _processProgressBars(progressBars) {
        const processedProgressBars = {};
        for (const fieldName in progressBars) {
            processedProgressBars[fieldName] = {};
            const progressBarInfo = progressBars[fieldName];
            for (const [resId, progressBar] of Object.entries(progressBarInfo)) {
                processedProgressBars[fieldName][resId] = this._processProgressBar(
                    progressBar,
                    progressBarInfo.warning
                );
            }
        }
        return processedProgressBars;
    }

    _processUnavailabilities(unavailabilities) {
        const processedUnavailabilities = {};
        for (const fieldName in unavailabilities) {
            processedUnavailabilities[fieldName] = {};
            for (const [resId, resUnavailabilities] of Object.entries(
                unavailabilities[fieldName]
            )) {
                processedUnavailabilities[fieldName][resId] = resUnavailabilities.map((u) => ({
                    start: deserializeDateTime(u.start),
                    stop: deserializeDateTime(u.stop),
                }));
            }
        }
        return processedUnavailabilities;
    }

    /**
     * @template {Record<string, any>} T
     * @param {T} schedule
     * @returns {Partial<T>}
     */
    _scheduleToData(schedule) {
        const allowedFields = [
            this.metaData.dateStartField,
            this.metaData.dateStopField,
            ...this.metaData.groupedBy,
        ];
        return pick(schedule, ...allowedFields);
    }
}
