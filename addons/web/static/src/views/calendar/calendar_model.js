// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { makeContext } from "@web/core/context";
import { makeLogger } from "@web/core/debug/debug_logger";
import { reportUncaught } from "@web/core/errors/error_utils";
import { getFieldCodec } from "@web/core/field_codec";
import { isX2Many } from "@web/core/field_types";
import {
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { DateTime } from "@web/core/l10n/luxon";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { groupBy } from "@web/core/utils/collections/arrays";
import { Cache } from "@web/core/utils/collections/cache";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { formatFloat } from "@web/core/utils/format/numbers";
import { useDebounced } from "@web/core/utils/timing";
import { Model } from "@web/model/model";
import { extractFieldsFromArchInfo } from "@web/model/relational_model";
import {
    CLIENT_AGGREGATORS,
    computeAggregatedValue,
} from "@web/views/view_measurements";

import {
    computeCalendarRange,
    computeFiltersDomain,
    computeRangeDomain,
} from "./calendar_date_range.js";
import { normalizeCalendarRecord } from "./calendar_record.js";

function collectDynamicRawFilters(
    data,
    field,
    /** @type {string} */ fieldName,
    addFilterFields,
) {
    const rawFiltersById = new Map();
    for (const record of Object.values(data.records)) {
        let rawValues = isX2Many(field)
            ? record.rawRecord[fieldName]
            : [record.rawRecord[fieldName]];
        if (!rawValues.length) {
            rawValues = [false];
        }
        for (const rawValue of rawValues) {
            const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
            if (!rawFiltersById.has(value)) {
                rawFiltersById.set(value, {
                    id: value,
                    [fieldName]: rawValue,
                    ...addFilterFields(record),
                });
            }
        }
    }
    return [...rawFiltersById.values()];
}

/** @returns {Promise<Record<string, any>[]>} */
async function fetchDynamicFilterColors(
    orm,
    meta,
    rawFilters,
    /** @type {string} */ fieldName,
    filterInfo,
) {
    const { fields, fieldMapping } = meta;
    const field = fields[fieldName];
    const relatedIds = rawFilters.map((f) => f.id).filter((id) => id);
    if (!relatedIds.length || !field.relation) {
        return [];
    }
    const fieldIsX2Many = isX2Many(field);
    const fieldsToFetch = [];
    const { colorFieldName } = filterInfo;
    const shouldFetchColor =
        colorFieldName &&
        (!fieldMapping.color ||
            `${fieldName}.${colorFieldName}` !== fields[fieldMapping.color].related);
    if (shouldFetchColor) {
        fieldsToFetch.push(colorFieldName);
    }
    if (fieldIsX2Many) {
        fieldsToFetch.push("display_name");
    }
    if (!fieldsToFetch.length) {
        return [];
    }
    const records = await orm.searchRead(
        field.relation,
        [["id", "in", relatedIds]],
        fieldsToFetch,
        { context: { active_test: false } },
    );
    if (fieldIsX2Many) {
        const nameById = Object.fromEntries(records.map((r) => [r.id, r.display_name]));
        for (const rawFilter of rawFilters) {
            const id = rawFilter.id;
            if (!id || !nameById[id]) {
                continue;
            }
            rawFilter[fieldName] = [id, nameById[id]];
        }
    }
    return shouldFetchColor ? records : [];
}

const log = makeLogger("web.view.calendar");

export class CalendarModel extends Model {
    static DEBOUNCED_LOAD_DELAY = 600;
    static services = ["notification"];

    /**
     * @param {Object} params
     * @param {{ notification: Object }} services
     */
    setup(params, { notification }) {
        /** @protected */
        this.keepLast = new KeepLast({ rejectSuperseded: true });
        this.notification = notification;

        const formViewFromConfig = (this.env.config.views || []).find(
            (/** @type {[number | false, string]} */ view) => view[1] === "form",
        );
        const formViewIdFromConfig = formViewFromConfig ? formViewFromConfig[0] : false;
        const fieldNodes = params.popoverFieldNodes;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            /** @type {any} */ ({ fieldNodes }),
            params.fields,
        );
        this.meta = {
            ...params,
            activeFields,
            fields,
            firstDayOfWeek: (localization.weekStart || 0) % 7,
            formViewId: params.formViewId || formViewIdFromConfig,
        };
        if (this.meta.aggregate) {
            const [field, explicitAggregator] = this.meta.aggregate.split(":");
            const aggregator =
                explicitAggregator || this.fields[field].aggregator || "sum";
            this.meta.aggregate = CLIENT_AGGREGATORS.has(aggregator)
                ? `${field}:${aggregator}`
                : `${field}:sum`;
        }
        this.meta.scale = this.getLocalStorageScale();
        this.data = {
            filterSections: {},
            range: null,
            records: {},
            unusualDays: [],
        };

        const debouncedLoadDelay = /** @type {any} */ (this.constructor)
            .DEBOUNCED_LOAD_DELAY;
        this.debouncedLoad = useDebounced(
            (params) => this.load(params),
            debouncedLoadDelay,
        );

        this._unusualDaysCache = new Cache(
            (data) => this.fetchUnusualDays(data),
            (data) =>
                `${serializeDateTime(data.range.start)},${serializeDateTime(data.range.end)},${JSON.stringify(this.meta.context ?? {})}`,
        );
    }
    /** @param {Object} [params] */
    async load(params = {}) {
        // Concurrent loads share meta; only published metadata is a rollback point.
        this.publishedMeta ??= { ...this.meta };
        Object.assign(this.meta, params);
        if (!this.meta.date) {
            this.meta.date =
                params.context && params.context.initial_date
                    ? deserializeDateTime(params.context.initial_date).startOf("day")
                    : DateTime.local().startOf("day");
        }
        if (!this.meta.scales.includes(this.meta.scale)) {
            this.meta.scale = this.meta.scales[0];
        }
        const data = { ...this.data };
        log.pipeline("load", () => ({
            resModel: this.meta.resModel,
            scale: this.meta.scale,
            date: this.meta.date?.toISODate(),
            params: Object.keys(params),
        }));
        const endLoad = log.perf(`updateData ${this.meta.resModel}`);
        try {
            await this.keepLast.add(this.updateData(data));
        } catch (error) {
            if (error instanceof SupersededError) {
                endLoad({ superseded: true });
                return;
            }
            for (const key of Object.keys(this.meta)) {
                if (!(key in this.publishedMeta)) {
                    delete this.meta[key];
                }
            }
            Object.assign(this.meta, this.publishedMeta);
            endLoad({ failed: true });
            throw error;
        }
        endLoad({ records: Object.keys(data.records || {}).length });
        browser.localStorage.setItem(this.storageKey, this.meta.scale);
        this.data = data;
        this.publishedMeta = { ...this.meta };
        this.notify();
    }

    get aggregate() {
        return this.meta.aggregate;
    }
    get date() {
        return this.meta.date;
    }
    get canCreate() {
        return this.meta.canCreate;
    }
    get canDelete() {
        return this.meta.canDelete;
    }
    get canEdit() {
        return (
            this.meta.canEdit &&
            !this.meta.fields[this.meta.fieldMapping.date_start].readonly
        );
    }
    get dateStartType() {
        return this.fields[this.fieldMapping.date_start].type;
    }
    get dateStopType() {
        if (this.fieldMapping.date_stop) {
            return this.fields[this.fieldMapping.date_stop].type;
        }
        return null;
    }
    get eventLimit() {
        return this.meta.eventLimit;
    }
    get exportedState() {
        return { date: this.meta.date };
    }
    get fieldMapping() {
        return this.meta.fieldMapping;
    }
    get fields() {
        return this.meta.fields;
    }
    get filterSections() {
        return Object.values(this.data.filterSections);
    }
    get firstDayOfWeek() {
        return this.meta.firstDayOfWeek;
    }
    get formViewId() {
        return this.meta.formViewId;
    }
    get hasAllDaySlot() {
        return (
            this.meta.fieldMapping.all_day ||
            this.meta.fields[this.meta.fieldMapping.date_start].type === "date"
        );
    }
    get hasEditDialog() {
        return this.meta.hasEditDialog;
    }
    get hasMultiCreate() {
        return (
            !!this.meta.multiCreateView &&
            !this.env.isSmall &&
            this.meta.scale === "month"
        );
    }
    get hasQuickCreate() {
        return this.meta.quickCreate;
    }
    get isDateHidden() {
        return this.meta.isDateHidden;
    }
    get isTimeHidden() {
        return this.meta.isTimeHidden;
    }
    get monthOverflow() {
        return this.meta.monthOverflow;
    }
    get popoverFieldNodes() {
        return this.meta.popoverFieldNodes;
    }
    get activeFields() {
        return this.meta.activeFields;
    }
    get rangeEnd() {
        return this.data.range.end;
    }
    get rangeStart() {
        return this.data.range.start;
    }
    get records() {
        return this.data.records;
    }
    get resModel() {
        return this.meta.resModel;
    }
    get scale() {
        return this.meta.scale;
    }
    get scales() {
        return this.meta.scales;
    }
    get showDatePicker() {
        return this.meta.showDatePicker;
    }
    get showMultiCreateTimeRange() {
        return this.dateStartType === "datetime" && this.dateStopType === "datetime";
    }
    get storageKey() {
        return `scaleOf-viewId-${this.env.config.viewId}`;
    }
    get unusualDays() {
        return this.data.unusualDays;
    }
    get quickCreateFormViewId() {
        return this.meta.quickCreateViewId;
    }
    get defaultFilterLabel() {
        return _t("Undefined");
    }

    async createFilter(/** @type {string} */ fieldName, filterValue) {
        const info = this.meta.filtersInfo[fieldName];
        if (!info || !info.writeFieldName || !info.writeResModel) {
            return;
        }

        const normalizedFilterValue = Array.isArray(filterValue)
            ? filterValue
            : [filterValue];
        const dataArray = normalizedFilterValue.map((value) => {
            const data = {
                user_id: user.userId,
                [info.writeFieldName]: value,
            };
            if (info.filterFieldName) {
                data[info.filterFieldName] = true;
            }
            return data;
        });

        await this.orm.create(info.writeResModel, dataArray);
        await this.load();
    }
    async createRecord(record) {
        log.logic("createRecord", () => ({ resModel: this.meta.resModel, record }));
        const rawRecord = this.buildRawRecord(record);
        const context = this.makeContextDefaults(rawRecord);
        await this.orm.create(this.meta.resModel, [rawRecord], { context });
        this.invalidateUnusualDays();
        await this.load();
    }

    invalidateUnusualDays() {
        this._unusualDaysCache.invalidate();
    }

    /**
     * @param {Object} multiCreateData
     * @param {any[]} dates
     * @returns {Promise<*>}
     */
    async multiCreateRecords(multiCreateData, dates) {
        const records = [];
        const values = await multiCreateData.record.getChanges();
        const timeRange = multiCreateData.timeRange;

        const [section] = this.filterSections;
        const assignableFilters = section
            ? section.filters.filter((filter) =>
                  ["record", "user"].includes(filter.type),
              )
            : [];
        for (const date of dates) {
            const initialRecordValue = {};
            if (this.showMultiCreateTimeRange) {
                initialRecordValue.start = date.plus(timeRange.start.toObject());
                initialRecordValue.end = date.plus(timeRange.end.toObject());
            } else {
                initialRecordValue.start = date;
            }
            const rawRecord = this.buildRawRecord(initialRecordValue);
            if (!assignableFilters.length) {
                records.push({
                    ...rawRecord,
                    ...values,
                });
                continue;
            }
            for (const filter of assignableFilters) {
                if (filter.active && filter.value) {
                    records.push({
                        ...rawRecord,
                        ...values,
                        [section.fieldName]: filter.value,
                    });
                }
            }
        }
        if (!records.length && dates.length) {
            this.notification.add(
                _t(
                    "Activate at least one record in the side panel to assign the new events to.",
                ),
                { type: "warning" },
            );
        }
        if (records.length) {
            const createdRecords = await this.orm.create(this.meta.resModel, records, {
                context: this.meta.context,
            });
            this.invalidateUnusualDays();
            await this.load();
            return createdRecords;
        }
        return [];
    }

    async unlinkFilter(/** @type {string} */ fieldName, recordId) {
        const info = this.meta.filtersInfo[fieldName];
        const section = this.data.filterSections[fieldName];
        if (section) {
            this.keepLast.cancel();
            section.filters = section.filters.filter((f) => f.recordId !== recordId);
        }
        if (info?.writeResModel) {
            try {
                await this.orm.unlink(info.writeResModel, [recordId]);
            } finally {
                await this.debouncedLoad().catch(reportUncaught);
            }
        }
    }
    async unlinkRecord(recordId) {
        log.logic("unlinkRecord", () => ({ resModel: this.meta.resModel, recordId }));
        await this.orm.unlink(this.meta.resModel, [recordId]);
        this.invalidateUnusualDays();
        await this.load();
    }

    async unlinkRecords(recordsId) {
        if (recordsId.length) {
            await this.orm.unlink(this.meta.resModel, recordsId);
            this.invalidateUnusualDays();
            await this.load();
        }
    }

    async updateFilters(/** @type {string} */ fieldName, filters, active) {
        this.keepLast.cancel();
        for (const filter of filters) {
            filter.active = active;
        }
        const info = this.meta.filtersInfo[fieldName];
        try {
            if (
                info &&
                info.writeFieldName &&
                info.writeResModel &&
                info.filterFieldName
            ) {
                const filterIds = filters
                    .filter((f) => f.type === "record")
                    .map((f) => f.recordId);
                if (filterIds.length) {
                    const data = {
                        [info.filterFieldName]: active,
                    };
                    const context = this.meta.context;
                    await this.orm.write(info.writeResModel, filterIds, data, {
                        context,
                    });
                }
            }
        } finally {
            await this.debouncedLoad().catch(reportUncaught);
        }
    }
    async updateRecord(record, options = {}) {
        const rawRecord = this.buildRawRecord(record, options);
        delete rawRecord[this.meta.fieldMapping.create_name_field || "name"];
        try {
            await this.orm.write(this.meta.resModel, [record.id], rawRecord, {
                context: this.meta.context,
            });
        } finally {
            this.invalidateUnusualDays();
            await this.load().catch(reportUncaught);
        }
    }

    getAllDayDates(start, end) {
        return [start.set({ hours: 7 }), end.set({ hours: 19 })];
    }

    /**
     * @param {Object} partialRecord
     * @param {Object} [options]
     * @returns {Object}
     */
    buildRawRecord(partialRecord, options = {}) {
        const data = {};
        data[this.meta.fieldMapping.create_name_field || "name"] = partialRecord.title;

        let start = partialRecord.start;
        let end = partialRecord.end;

        if (!end || !end.isValid) {
            if (partialRecord.isAllDay) {
                end = start;
            } else {
                end = start.plus({ hours: options.duration_hour || 1 });
            }
        }

        const isDateEvent = this.dateStartType === "date";
        if (partialRecord.isAllDay) {
            if (!this.hasAllDaySlot && !isDateEvent && !partialRecord.id) {
                [start, end] = this.getAllDayDates(start, end);
            }
        }

        if (this.meta.fieldMapping.all_day) {
            data[this.meta.fieldMapping.all_day] = partialRecord.isAllDay;
        }

        data[this.meta.fieldMapping.date_start] =
            (partialRecord.isAllDay && this.hasAllDaySlot
                ? "date"
                : this.dateStartType) === "date"
                ? serializeDate(start)
                : serializeDateTime(start);

        if (this.meta.fieldMapping.date_stop) {
            data[this.meta.fieldMapping.date_stop] =
                (partialRecord.isAllDay && this.hasAllDaySlot
                    ? "date"
                    : this.dateStopType) === "date"
                    ? serializeDate(end)
                    : serializeDateTime(end);
        }

        if (this.meta.fieldMapping.date_delay) {
            if (this.meta.scale !== "month" || !options.moved) {
                data[this.meta.fieldMapping.date_delay] = end.diff(
                    start,
                    "hours",
                ).hours;
            }
        }
        return data;
    }
    /**
     * @param {Object} rawRecord
     * @returns {Object}
     */
    makeContextDefaults(rawRecord) {
        const { fieldMapping, scale } = this.meta;

        const context = { ...this.meta.context };
        const fieldNames = [
            fieldMapping.create_name_field || "name",
            fieldMapping.date_start,
            fieldMapping.date_stop,
            fieldMapping.date_delay,
            fieldMapping.all_day || "allday",
        ];
        for (const fieldName of fieldNames) {
            if (rawRecord[fieldName] !== undefined) {
                context[`default_${fieldName}`] = rawRecord[fieldName];
            }
        }
        if (["month", "year"].includes(scale)) {
            context[`default_${fieldMapping.all_day || "allday"}`] = true;
        }

        return context;
    }

    /** @protected */
    async updateData(data) {
        data.range = this.computeRange();
        let unusualDaysProm;
        if (this.meta.showUnusualDays) {
            unusualDaysProm = this.loadUnusualDays(data).then((unusualDays) => {
                data.unusualDays = unusualDays;
            });
        }

        const { sections, dynamicFiltersInfo } = await this.loadFilters(data);

        data.filterSections = sections;
        data.records = await this.loadRecords(data);
        const dynamicSections = await this.loadDynamicFilters(data, dynamicFiltersInfo);

        Object.assign(data.filterSections, dynamicSections);

        for (const [fieldName, filterInfo] of Object.entries(dynamicSections)) {
            const field = this.meta.fields[fieldName];
            if (!field) {
                continue;
            }
            const inactiveFilters = filterInfo.filters.filter((f) => !f.active);
            if (!inactiveFilters.length) {
                continue;
            }
            const inactiveFilterVals = new Set(
                inactiveFilters.map((filter) => filter.value),
            );
            for (const [recordId, record] of Object.entries(data.records)) {
                const rawValue = record.rawRecord[fieldName];
                let remove;
                if (isX2Many(field)) {
                    remove = rawValue.length
                        ? rawValue.every((value) => inactiveFilterVals.has(value))
                        : inactiveFilterVals.has(false);
                } else {
                    const recordValue = Array.isArray(rawValue)
                        ? rawValue[0]
                        : rawValue;
                    remove = inactiveFilterVals.has(recordValue);
                }
                if (remove) {
                    delete data.records[recordId];
                }
            }
        }

        await unusualDaysProm;

        if (this.aggregate) {
            for (const [fieldName, { filters }] of Object.entries(
                data.filterSections,
            )) {
                const aggregates = this.computeAggregatedValues(fieldName, data);
                for (const filter of filters) {
                    filter.aggregatedValue = aggregates[filter.value] || 0;
                }
            }
        }
    }

    /** @protected */
    computeRange() {
        const { scale, date, firstDayOfWeek } = this.meta;
        return computeCalendarRange(scale, date, firstDayOfWeek, this.monthOverflow);
    }

    /**
     * @param {string} fieldName
     * @param {Object} [data=this.data]
     */
    computeAggregatedValues(fieldName, data = this.data) {
        const records = Object.values(data.records);
        const fieldType = this.meta.fields[fieldName].type;
        const groups = groupBy(records, ({ rawRecord }) => {
            const rawValue = rawRecord[fieldName];
            return fieldType === "many2one" ? rawValue?.[0] || false : rawValue;
        });
        const aggregates = {};
        const [aggregateField, aggregator] = this.aggregate.split(":");
        for (const [group, groupRecords] of Object.entries(groups)) {
            const values = /** @type {typeof records} */ (groupRecords)
                .map(({ rawRecord }) => rawRecord[aggregateField])
                .filter((value) => typeof value === "number");
            if (!values.length) {
                aggregates[group] = formatFloat(0, { trailingZeros: false });
                continue;
            }
            aggregates[group] = formatFloat(
                computeAggregatedValue(values, aggregator),
                {
                    trailingZeros: false,
                },
            );
        }
        return aggregates;
    }
    /** @protected */
    computeDomain(data) {
        return [
            ...this.meta.domain,
            ...this.computeRangeDomain(data),
            ...this.computeFiltersDomain(data),
        ];
    }
    /** @protected */
    computeFiltersDomain(data) {
        return computeFiltersDomain(data.filterSections, this.meta.filtersInfo);
    }
    /** @protected */
    computeRangeDomain(data) {
        return computeRangeDomain(
            this.meta.fieldMapping,
            this.dateStartType,
            data.range,
        );
    }

    /** @protected */
    fetchUnusualDays(data) {
        return this.orm.call(
            this.meta.resModel,
            "get_unusual_days",
            [serializeDateTime(data.range.start), serializeDateTime(data.range.end)],
            { context: this.meta.context },
        );
    }
    /** @protected */
    async loadUnusualDays(data) {
        const unusualDays = await this._unusualDaysCache.read(data);
        return Object.entries(unusualDays)
            .filter((entry) => entry[1])
            .map((entry) => entry[0]);
    }

    /** @protected */
    fetchRecords(data) {
        const { context, fieldNames, resModel } = this.meta;
        return this.orm.searchRead(
            resModel,
            this.computeDomain(data),
            [...new Set([...fieldNames, ...Object.keys(this.meta.activeFields)])],
            { context },
        );
    }
    /** @protected */
    async loadRecords(data) {
        const rawRecords = await this.fetchRecords(data);
        const records = {};
        for (const rawRecord of rawRecords) {
            records[rawRecord.id] = this.normalizeRecord(rawRecord);
        }
        return records;
    }
    /**
     * @protected
     * @param {Record<string, any>} rawRecord
     */
    normalizeRecord(rawRecord) {
        return normalizeCalendarRecord(rawRecord, {
            fields: this.meta.fields,
            fieldMapping: this.meta.fieldMapping,
            isTimeHidden: this.meta.isTimeHidden,
            scale: this.meta.scale,
            isSmall: this.env.isSmall,
        });
    }

    /** @protected */
    addFilterFields(record, filterInfo) {
        return {
            colorIndex: record.colorIndex,
        };
    }

    /** @protected */
    fetchFilters(/** @type {string} */ resModel, /** @type {string[]} */ fieldNames) {
        return this.orm.searchRead(
            resModel,
            [["user_id", "=", user.userId]],
            fieldNames,
        );
    }

    getLocalStorageScale() {
        const localScaleId = browser.localStorage.getItem(this.storageKey);
        return this.meta.scales.includes(localScaleId) ? localScaleId : this.meta.scale;
    }

    /** @protected */
    async loadFilters(data) {
        const previousSections = data.filterSections;
        const sections = {};
        const dynamicFiltersInfo = {};
        const proms = [];
        for (const [fieldName, filterInfo] of Object.entries(this.meta.filtersInfo)) {
            const previousSection = previousSections[fieldName];
            if (filterInfo.writeResModel) {
                const prom = this.loadFilterSection(
                    fieldName,
                    filterInfo,
                    previousSection,
                ).then((result) => {
                    sections[fieldName] = result;
                });
                proms.push(prom);
            } else {
                dynamicFiltersInfo[fieldName] = { filterInfo, previousSection };
            }
        }
        await Promise.all(proms);
        return { sections, dynamicFiltersInfo };
    }
    /** @protected */
    async loadFilterSection(
        /** @type {string} */ fieldName,
        filterInfo,
        previousSection,
    ) {
        const { filterFieldName, writeFieldName, writeResModel } = filterInfo;
        const fields = [writeFieldName, filterFieldName].filter(Boolean);
        const rawFilters = await this.fetchFilters(writeResModel, fields);
        const previousFilters = previousSection ? previousSection.filters : [];

        const previousRecordFilters = new Map();
        for (const filter of previousFilters) {
            if (filter.type === "record") {
                previousRecordFilters.set(filter.recordId, filter);
            }
        }
        const filters = rawFilters.map((rawFilter) =>
            this.makeFilterRecord(
                filterInfo,
                previousRecordFilters.get(rawFilter.id),
                rawFilter,
            ),
        );

        const field = this.meta.fields[fieldName];
        const isUserOrPartner = ["res.users", "res.partner"].includes(field.relation);
        if (isUserOrPartner) {
            const previousUserFilter = previousFilters.find((f) => f.type === "user");
            filters.push(
                this.makeFilterUser(
                    filterInfo,
                    previousUserFilter,
                    fieldName,
                    rawFilters,
                ),
            );
        }

        return {
            label: filterInfo.label,
            fieldName,
            filters,
            avatar: {
                field: filterInfo.avatarFieldName,
                model: filterInfo.resModel,
            },
            hasAvatar: !!filterInfo.avatarFieldName,
            write: {
                field: writeFieldName,
                model: writeResModel,
            },
            canAddFilter: !!filterInfo.writeResModel,
            context: makeContext([filterInfo.context, this.meta.context]),
        };
    }
    /** @protected */
    async loadDynamicFilters(data, filtersInfo) {
        const sections = {};
        const proms = [];
        for (const [fieldName, { filterInfo, previousSection }] of Object.entries(
            filtersInfo,
        )) {
            const prom = this.loadDynamicFilterSection(
                data,
                fieldName,
                filterInfo,
                previousSection,
            ).then((result) => {
                sections[fieldName] = result;
            });
            proms.push(prom);
        }
        await Promise.all(proms);
        return sections;
    }
    /** @protected */
    async loadDynamicFilterSection(
        data,
        /** @type {string} */ fieldName,
        filterInfo,
        previousSection,
    ) {
        const previousFilters = previousSection ? previousSection.filters : [];
        const rawFilters = collectDynamicRawFilters(
            data,
            this.meta.fields[fieldName],
            fieldName,
            (record) => this.addFilterFields(record, filterInfo),
        );
        const rawColors = await fetchDynamicFilterColors(
            this.orm,
            this.meta,
            rawFilters,
            fieldName,
            filterInfo,
        );
        const colorById = new Map(rawColors.map((raw) => [raw.id, raw]));

        const previousDynamicFilters = new Map();
        for (const filter of previousFilters) {
            if (filter.type === "dynamic") {
                previousDynamicFilters.set(filter.value, filter);
            }
        }
        const filters = rawFilters.map((rawFilter) =>
            this.makeFilterDynamic(
                filterInfo,
                previousDynamicFilters.get(rawFilter.id),
                fieldName,
                rawFilter,
                colorById,
            ),
        );

        return {
            label: filterInfo.label,
            fieldName,
            filters,
            avatar: {
                field: filterInfo.avatarFieldName,
                model: filterInfo.resModel,
            },
            hasAvatar: !!filterInfo.avatarFieldName,
            write: {
                field: filterInfo.writeFieldName,
                model: filterInfo.writeResModel,
            },
            canAddFilter: !!filterInfo.writeResModel,
        };
    }

    /** @protected */
    /** @protected */
    makeFilterDynamic(
        filterInfo,
        previousFilter,
        /** @type {string} */ fieldName,
        rawFilter,
        rawColors,
    ) {
        const { fieldMapping, fields } = this.meta;
        const rawValue = rawFilter[fieldName];
        const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
        const field = fields[fieldName];
        const fieldIsX2Many = isX2Many(field);
        const formatter = getFieldCodec(fieldIsX2Many ? "many2one" : field.type).format;

        const { colorFieldName } = filterInfo;
        const colorField = fields[fieldMapping.color];
        const hasFilterColorAttr = !!colorFieldName;
        const sameRelatedModel =
            colorField &&
            (colorField.relation === field.relation ||
                (colorField.related && colorField.related.startsWith(`${fieldName}.`)));
        let colorIndex = null;
        if (hasFilterColorAttr || sameRelatedModel) {
            colorIndex = rawFilter.colorIndex;
        }
        if (rawColors.size) {
            const rawColor = rawColors.get(value);
            colorIndex = rawColor ? rawColor[colorFieldName] : 0;
        }

        return {
            type: "dynamic",
            recordId: null,
            value,
            label: formatter(rawValue, { field }) || this.defaultFilterLabel,
            active: previousFilter ? previousFilter.active : true,
            canRemove: false,
            colorIndex,
            hasAvatar: !!value,
        };
    }
    /** @protected */
    makeFilterRecord(filterInfo, previousFilter, rawRecord) {
        const { colorFieldName, filterFieldName, writeFieldName } = filterInfo;
        const { fields, fieldMapping } = this.meta;
        const raw = rawRecord[writeFieldName];
        const value = Array.isArray(raw) ? raw[0] : raw;
        const field = fields[writeFieldName];
        const fieldIsX2Many = isX2Many(field);
        const formatter = getFieldCodec(fieldIsX2Many ? "many2one" : field.type).format;

        const colorField = fields[fieldMapping.color];
        const colorValue =
            colorField &&
            (() => {
                const sameRelatedModel = colorField.relation === field.relation;
                const sameRelatedField =
                    colorField.related === `${writeFieldName}.${colorFieldName}`;
                const shouldHaveColor = sameRelatedModel || sameRelatedField;
                const colorToUse = raw ? value : rawRecord[fieldMapping.color];
                return shouldHaveColor ? colorToUse : null;
            })();
        const colorIndex = Array.isArray(colorValue) ? colorValue[0] : colorValue;

        let active = false;
        if (filterFieldName) {
            active = rawRecord[filterFieldName];
        } else if (previousFilter) {
            active = previousFilter.active;
        }
        return {
            type: "record",
            recordId: rawRecord.id,
            value,
            label: formatter(raw),
            active,
            canRemove: true,
            colorIndex,
            hasAvatar: !!value,
        };
    }
    /** @protected */
    makeFilterUser(
        filterInfo,
        previousFilter,
        /** @type {string} */ fieldName,
        rawRecords,
    ) {
        const field = this.meta.fields[fieldName];
        const userFieldName = field.relation === "res.partner" ? "partnerId" : "userId";
        const value = user[userFieldName];

        let colorIndex = value;
        const rawRecord = rawRecords.find(
            (r) =>
                Array.isArray(r[filterInfo.writeFieldName]) &&
                r[filterInfo.writeFieldName][0] === value,
        );
        if (filterInfo.colorFieldName && rawRecord) {
            const colorValue = rawRecord[filterInfo.colorFieldName];
            colorIndex = Array.isArray(colorValue) ? colorValue[0] : colorValue;
        }

        return {
            type: "user",
            recordId: null,
            value,
            label: user.name,
            active: previousFilter ? previousFilter.active : true,
            canRemove: false,
            colorIndex,
            hasAvatar: !!value,
        };
    }
}
