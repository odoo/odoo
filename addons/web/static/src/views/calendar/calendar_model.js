import {
    serializeDate,
    serializeDateTime,
    deserializeDate,
    deserializeDateTime,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/model/model";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { browser } from "@web/core/browser/browser";
import { makeContext } from "@web/core/context";
import { groupBy } from "@web/core/utils/arrays";
import { Cache } from "@web/core/utils/cache";
import { formatFloat } from "@web/core/utils/numbers";
import { useDebounced } from "@web/core/utils/timing";
import { computeAggregatedValue } from "@web/views/utils";

const { DateTime } = luxon;

export class CalendarModel extends Model {
    static DEBOUNCED_LOAD_DELAY = 600;
    static services = ["notification"];

    setup(params, { notification }) {
        /** @protected */
        this.keepLast = new KeepLast();
        this.notification = notification;

        const formViewFromConfig = (this.env.config.views || []).find((view) => view[1] === "form");
        const formViewIdFromConfig = formViewFromConfig ? formViewFromConfig[0] : false;
        const fieldNodes = params.popoverFieldNodes;
        const { activeFields, fields } = extractFieldsFromArchInfo({ fieldNodes }, params.fields);
        this.meta = {
            ...params,
            activeFields,
            fields,
            firstDayOfWeek: (localization.weekStart || 0) % 7,
            formViewId: params.formViewId || formViewIdFromConfig,
        };
        if (this.meta.aggregate?.split(":").length === 1) {
            const aggregator = this.fields[this.meta.aggregate].aggregator || "sum";
            this.meta.aggregate = `${this.meta.aggregate}:${aggregator}`;
        }
        this.meta.scale = this.getLocalStorageScale();
        this.data = {
            filterSections: {},
            range: null,
            records: {},
            unusualDays: [],
        };

        const debouncedLoadDelay = this.constructor.DEBOUNCED_LOAD_DELAY;
        this.debouncedLoad = useDebounced((params) => this.load(params), debouncedLoadDelay);

        this._unusualDaysCache = new Cache(
            (data) => this.fetchUnusualDays(data),
            (data) => `${serializeDateTime(data.range.start)},${serializeDateTime(data.range.end)}`
        );
    }
    async load(params = {}) {
        Object.assign(this.meta, params);
        if (!this.meta.date) {
            this.meta.date =
                params.context && params.context.initial_date
                    ? deserializeDateTime(params.context.initial_date).startOf("day")
                    : DateTime.local().startOf("day");
        }
        // Prevent picking a scale that is not supported by the view
        if (!this.meta.scales.includes(this.meta.scale)) {
            this.meta.scale = this.meta.scales[0];
        }
        browser.localStorage.setItem(this.storageKey, this.meta.scale);
        const data = { ...this.data };
        await this.keepLast.add(this.updateData(data));
        this.data = data;
        this.notify();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
        return this.meta.canEdit && !this.meta.fields[this.meta.fieldMapping.date_start].readonly;
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
        return !!this.meta.multiCreateView && !this.env.isSmall;
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

    //--------------------------------------------------------------------------

    async createFilter(fieldName, filterValue) {
        const info = this.meta.filtersInfo[fieldName];
        if (!info || !info.writeFieldName || !info.writeResModel) {
            return;
        }

        const normalizedFilterValue = Array.isArray(filterValue) ? filterValue : [filterValue];
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
        const rawRecord = this.buildRawRecord(record);
        const context = this.makeContextDefaults(rawRecord);
        await this.orm.create(this.meta.resModel, [rawRecord], { context });
        await this.load();
    }

    /**
     * Create multi records of the specify dates and values.
     * Optionally time range can be specified to set the start and end time.
     * Also, if there is a filter section, the first filter section will be chosen as additional value for the record.
     *
     * @param {Object} multiCreateData
     * @param {DateTime[]} dates array of Date
     * @returns {Promise<*>}
     */
    async multiCreateRecords(multiCreateData, dates) {
        const records = [];
        const values = await multiCreateData.record.getChanges();
        const timeRange = multiCreateData.timeRange;

        // we deliberately only use the values of the first filter section, to avoid combinatorial explosion
        const [section] = this.filterSections;
        for (const date of dates) {
            const initialRecordValue = {};
            if (this.showMultiCreateTimeRange) {
                initialRecordValue.start = date.plus(timeRange.start.toObject());
                initialRecordValue.end = date.plus(timeRange.end.toObject());
            } else {
                initialRecordValue.start = date;
            }
            const rawRecord = this.buildRawRecord(initialRecordValue);
            if (!section) {
                records.push({
                    ...rawRecord,
                    ...values,
                });
                continue;
            }
            for (const filter of section.filters) {
                if (filter.active && filter.type === "record") {
                    records.push({
                        ...rawRecord,
                        ...values,
                        [section.fieldName]: filter.value,
                    });
                }
            }
        }
        if (records.length) {
            const createdRecords = await this.orm.create(this.meta.resModel, records, {
                context: this.meta.context,
            });
            this.load();
            return createdRecords;
        }
    }

    async unlinkFilter(fieldName, recordId) {
        const info = this.meta.filtersInfo[fieldName];
        const section = this.data.filterSections[fieldName];
        if (section) {
            // remove the filter directly, to provide a direct feedback to the user
            this.keepLast.add(Promise.resolve());
            section.filters = section.filters.filter((f) => f.recordId !== recordId);
        }
        if (info && info.writeResModel) {
            await this.orm.unlink(info.writeResModel, [recordId]);
            await this.debouncedLoad();
        }
    }
    async unlinkRecord(recordId) {
        await this.orm.unlink(this.meta.resModel, [recordId]);
        await this.load();
    }

    async unlinkRecords(recordsId) {
        if (recordsId.length) {
            await this.orm.unlink(this.meta.resModel, recordsId);
            await this.load();
        }
    }

    async updateFilters(fieldName, filters, active) {
        // update filters directly, to provide a direct feedback to the user
        this.keepLast.add(Promise.resolve());
        for (const filter of filters) {
            filter.active = active;
        }
        const info = this.meta.filtersInfo[fieldName];
        if (info && info.writeFieldName && info.writeResModel && info.filterFieldName) {
            const userFilter = filters.find((f) => f.type === "user");
            if (userFilter) {
                userFilter.active = active;
            }
            const filterIds = filters.filter((f) => f.type === "record").map((f) => f.recordId);
            if (filterIds) {
                const data = {
                    [info.filterFieldName]: active,
                };
                const context = this.meta.context;
                await this.orm.write(info.writeResModel, filterIds, data, { context });
            }
        }
        await this.debouncedLoad();
    }
    async updateRecord(record, options = {}) {
        const rawRecord = this.buildRawRecord(record, options);
        delete rawRecord.name; // name is immutable.
        await this.orm.write(this.meta.resModel, [record.id], rawRecord, {
            context: this.meta.context,
        });
        await this.load();
    }

    //--------------------------------------------------------------------------
    getAllDayDates(start, end) {
        return [start.set({ hours: 7 }), end.set({ hours: 19 })];
    }

    buildRawRecord(partialRecord, options = {}) {
        const data = {};
        data[this.meta.fieldMapping.create_name_field || "name"] = partialRecord.title;

        let start = partialRecord.start;
        let end = partialRecord.end;

        if (!end || !end.isValid) {
            // Set end date if not existing
            if (partialRecord.isAllDay) {
                end = start;
            } else {
                // in week mode or day mode, convert allday event to event
                end = start.plus({ hours: options.duration_hour || 1 });
            }
        }

        const isDateEvent = this.dateStartType === "date";
        // An "all day" event without the "all_day" option is not considered
        // as a 24h day. It's just a part of the day (by default: 7h-19h).
        if (partialRecord.isAllDay) {
            if (!this.hasAllDaySlot && !isDateEvent && !partialRecord.id) {
                // default hours in the user's timezone
                [start, end] = this.getAllDayDates(start, end);
            }
        }

        if (this.meta.fieldMapping.all_day) {
            data[this.meta.fieldMapping.all_day] = partialRecord.isAllDay;
        }

        data[this.meta.fieldMapping.date_start] =
            (partialRecord.isAllDay && this.hasAllDaySlot ? "date" : this.dateStartType) === "date"
                ? serializeDate(start)
                : serializeDateTime(start);

        if (this.meta.fieldMapping.date_stop) {
            data[this.meta.fieldMapping.date_stop] =
                (partialRecord.isAllDay && this.hasAllDaySlot ? "date" : this.dateStartType) ===
                "date"
                    ? serializeDate(end)
                    : serializeDateTime(end);
        }

        if (this.meta.fieldMapping.date_delay) {
            if (this.meta.scale !== "month" || !options.moved) {
                data[this.meta.fieldMapping.date_delay] = end.diff(start, "hours").hours;
            }
        }
        return data;
    }
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
            // fieldName could be in rawRecord but not defined
            if (rawRecord[fieldName] !== undefined) {
                context[`default_${fieldName}`] = rawRecord[fieldName];
            }
        }
        if (["month", "year"].includes(scale)) {
            context[`default_${fieldMapping.all_day || "allday"}`] = true;
        }

        return context;
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * @protected
     */
    async updateData(data) {
        data.range = this.computeRange();
        let unusualDaysProm;
        if (this.meta.showUnusualDays) {
            unusualDaysProm = this.loadUnusualDays(data).then((unusualDays) => {
                data.unusualDays = unusualDays;
            });
        }

        const { sections, dynamicFiltersInfo } = await this.loadFilters(data);

        // Load records and dynamic filters only with fresh filters
        data.filterSections = sections;
        data.records = await this.loadRecords(data);
        const dynamicSections = await this.loadDynamicFilters(data, dynamicFiltersInfo);

        // Apply newly computed filter sections
        Object.assign(data.filterSections, dynamicSections);

        // Remove records that don't match dynamic filters
        for (const [recordId, record] of Object.entries(data.records)) {
            for (const [fieldName, filterInfo] of Object.entries(dynamicSections)) {
                for (const filter of filterInfo.filters) {
                    const rawValue = record.rawRecord[fieldName];
                    const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
                    if (filter.value === value && !filter.active) {
                        delete data.records[recordId];
                    }
                }
            }
        }

        await unusualDaysProm;

        // Compute aggregate values
        if (this.aggregate) {
            for (const [fieldName, { filters }] of Object.entries(data.filterSections)) {
                const aggregates = this.computeAggregatedValues(fieldName, data);
                for (const filter of filters) {
                    filter.aggregatedValue = aggregates[filter.value] || 0;
                }
            }
        }
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     */
    computeRange() {
        const { scale, date, firstDayOfWeek } = this.meta;
        let start = date;
        let end = date;

        if (scale !== "week") {
            // startOf("week") does not depend on locale and will always give the
            // "Monday" of the week...
            start = start.startOf(scale);
            end = end.endOf(scale);
        }

        if (scale === "week" || (scale === "month" && this.monthOverflow)) {
            const currentWeekOffset = (start.weekday - firstDayOfWeek + 7) % 7;
            start = start.minus({ days: currentWeekOffset });
            end = start.plus({ weeks: scale === "week" ? 1 : 6, days: -1 });
        }

        start = start.startOf("day");
        end = end.endOf("day");

        return { start, end };
    }

    //--------------------------------------------------------------------------

    /**
     * @param {string} fieldName
     * @param {Object} [data=this.data]
     * @returns Object
     */
    computeAggregatedValues(fieldName, data = this.data) {
        const records = Object.values(data.records);
        const fieldType = this.meta.fields[fieldName].type;
        const groups = groupBy(records, ({ rawRecord }) => {
            const rawValue = rawRecord[fieldName];
            // FIXME: many2many not supported, but not supported for filters either
            return fieldType === "many2one" ? rawValue?.[0] || false : rawValue;
        });
        const aggregates = {};
        const [aggregateField, aggregator] = this.aggregate.split(":");
        for (const group in groups) {
            const values = groups[group].map(({ rawRecord }) => rawRecord[aggregateField]);
            aggregates[group] = formatFloat(computeAggregatedValue(values, aggregator), {
                trailingZeros: false,
            });
        }
        return aggregates;
    }
    /**
     * @protected
     */
    computeDomain(data) {
        return [
            ...this.meta.domain,
            ...this.computeRangeDomain(data),
            ...this.computeFiltersDomain(data),
        ];
    }
    /**
     * @protected
     */
    computeFiltersDomain(data) {
        // List authorized values for every field
        // fields with an active "all" filter are skipped
        const authorizedValues = {};
        const avoidValues = {};

        for (const [fieldName, filterSection] of Object.entries(data.filterSections)) {
            const filterSectionInfo = this.meta.filtersInfo[fieldName];
            // Loop over subfilters to complete authorizedValues
            for (const filter of filterSection.filters) {
                if (filterSectionInfo.writeResModel) {
                    if (!authorizedValues[fieldName]) {
                        authorizedValues[fieldName] = [];
                    }
                    if (filter.active) {
                        authorizedValues[fieldName].push(filter.value);
                    }
                } else {
                    if (!filter.active) {
                        if (!avoidValues[fieldName]) {
                            avoidValues[fieldName] = [];
                        }
                        avoidValues[fieldName].push(filter.value);
                    }
                }
            }
        }

        // Compute the domain
        const domain = [];
        for (const field in authorizedValues) {
            domain.push([field, "in", authorizedValues[field]]);
        }
        for (const field in avoidValues) {
            if (avoidValues[field].length > 0) {
                domain.push([field, "not in", avoidValues[field]]);
            }
        }
        return domain;
    }
    /**
     * @protected
     */
    computeRangeDomain(data) {
        const { fieldMapping } = this.meta;
        const serializeFn = this.dateStartType === "date" ? serializeDate : serializeDateTime;
        const formattedEnd = serializeFn(data.range.end);
        const formattedStart = serializeFn(data.range.start);

        const domain = [[fieldMapping.date_start, "<=", formattedEnd]];
        if (fieldMapping.date_stop) {
            domain.push([fieldMapping.date_stop, ">=", formattedStart]);
        } else if (!fieldMapping.date_delay) {
            domain.push([fieldMapping.date_start, ">=", formattedStart]);
        }
        return domain;
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     */
    fetchUnusualDays(data) {
        return this.orm.call(this.meta.resModel, "get_unusual_days", [
            serializeDateTime(data.range.start),
            serializeDateTime(data.range.end),
        ]);
    }
    /**
     * @protected
     */
    async loadUnusualDays(data) {
        const unusualDays = await this._unusualDaysCache.read(data);
        return Object.entries(unusualDays)
            .filter((entry) => entry[1])
            .map((entry) => entry[0]);
    }

    //--------------------------------------------------------------------------

    /**
     * @protected
     */
    fetchRecords(data) {
        const { context, fieldNames, resModel } = this.meta;
        return this.orm.searchRead(
            resModel,
            this.computeDomain(data),
            [...new Set([...fieldNames, ...Object.keys(this.meta.activeFields)])],
            { context }
        );
    }
    /**
     * @protected
     */
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
        const { fields, fieldMapping, isTimeHidden } = this.meta;

        const startType = fields[fieldMapping.date_start].type;
        const isAllDay =
            startType === "date" ||
            (fieldMapping.all_day && rawRecord[fieldMapping.all_day]) ||
            false;
        let start = isAllDay
            ? deserializeDate(rawRecord[fieldMapping.date_start])
            : deserializeDateTime(rawRecord[fieldMapping.date_start]);

        let end = start;
        let endType = startType;
        if (fieldMapping.date_stop) {
            endType = fields[fieldMapping.date_stop].type;
            end = isAllDay
                ? deserializeDate(rawRecord[fieldMapping.date_stop])
                : deserializeDateTime(rawRecord[fieldMapping.date_stop]);
        }

        const duration = rawRecord[fieldMapping.date_delay] || 1;

        if (isAllDay) {
            start = start.startOf("day");
            end = end.startOf("day");
        }
        if (!fieldMapping.date_stop && duration) {
            end = start.plus({ hours: duration });
        }

        const showTime =
            !(fieldMapping.all_day && rawRecord[fieldMapping.all_day]) &&
            startType !== "date" &&
            start.day === end.day;

        const colorValue = rawRecord[fieldMapping.color];
        const colorIndex = Array.isArray(colorValue) ? colorValue[0] : colorValue;

        const title = rawRecord[fieldMapping.create_name_field || "display_name"];

        return {
            id: rawRecord.id,
            title,
            isAllDay,
            start,
            startType,
            end,
            endType,
            duration,
            colorIndex,
            isHatched: rawRecord["is_hatched"] || false,
            isStriked: rawRecord["is_striked"] || false,
            isTimeHidden: isTimeHidden || !showTime,
            isMonth: this.meta.scale === "month",
            isSmall: this.env.isSmall,
            rawRecord,
        };
    }

    /**
     * @protected
     */
    addFilterFields(record, filterInfo) {
        return {
            colorIndex: record.colorIndex,
        };
    }
    //--------------------------------------------------------------------------

    /**
     * @protected
     */
    fetchFilters(resModel, fieldNames) {
        return this.orm.searchRead(resModel, [["user_id", "=", user.userId]], fieldNames);
    }

    getLocalStorageScale() {
        const localScaleId = browser.localStorage.getItem(this.storageKey);
        return this.meta.scales.includes(localScaleId) ? localScaleId : this.meta.scale;
    }

    /**
     * @protected
     */
    async loadFilters(data) {
        const previousSections = data.filterSections;
        const sections = {};
        const dynamicFiltersInfo = {};
        const proms = [];
        for (const [fieldName, filterInfo] of Object.entries(this.meta.filtersInfo)) {
            const previousSection = previousSections[fieldName];
            if (filterInfo.writeResModel) {
                const prom = this.loadFilterSection(fieldName, filterInfo, previousSection).then(
                    (result) => {
                        sections[fieldName] = result;
                    }
                );
                proms.push(prom);
            } else {
                dynamicFiltersInfo[fieldName] = { filterInfo, previousSection };
            }
        }
        await Promise.all(proms);
        return { sections, dynamicFiltersInfo };
    }
    /**
     * @protected
     */
    async loadFilterSection(fieldName, filterInfo, previousSection) {
        const { filterFieldName, writeFieldName, writeResModel } = filterInfo;
        const fields = [writeFieldName, filterFieldName].filter(Boolean);
        const rawFilters = await this.fetchFilters(writeResModel, fields);
        const previousFilters = previousSection ? previousSection.filters : [];

        const filters = rawFilters.map((rawFilter) => {
            const previousRecordFilter = previousFilters.find(
                (f) => f.type === "record" && f.recordId === rawFilter.id
            );
            return this.makeFilterRecord(filterInfo, previousRecordFilter, rawFilter);
        });

        const field = this.meta.fields[fieldName];
        const isUserOrPartner = ["res.users", "res.partner"].includes(field.relation);
        if (isUserOrPartner) {
            const previousUserFilter = previousFilters.find((f) => f.type === "user");
            filters.push(
                this.makeFilterUser(filterInfo, previousUserFilter, fieldName, rawFilters)
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
    /**
     * @protected
     */
    async loadDynamicFilters(data, filtersInfo) {
        const sections = {};
        const proms = [];
        for (const [fieldName, { filterInfo, previousSection }] of Object.entries(filtersInfo)) {
            const prom = this.loadDynamicFilterSection(
                data,
                fieldName,
                filterInfo,
                previousSection
            ).then((result) => {
                sections[fieldName] = result;
            });
            proms.push(prom);
        }
        await Promise.all(proms);
        return sections;
    }
    /**
     * @protected
     */
    async loadDynamicFilterSection(data, fieldName, filterInfo, previousSection) {
        const { fields, fieldMapping } = this.meta;
        const field = fields[fieldName];
        const previousFilters = previousSection ? previousSection.filters : [];

        const rawFilters = Object.values(data.records).reduce((filters, record) => {
            // FIXME: doesn't work for many2many/one2Many
            const rawValues = ["many2many", "one2many"].includes(field.type)
                ? record.rawRecord[fieldName]
                : [record.rawRecord[fieldName]];

            for (const rawValue of rawValues) {
                const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
                if (!filters.find((f) => f.id === value)) {
                    filters.push({
                        id: value,
                        [fieldName]: rawValue,
                        ...this.addFilterFields(record, filterInfo),
                    });
                }
            }
            return filters;
        }, []);

        const { colorFieldName } = filterInfo;
        const shouldFetchColor =
            colorFieldName &&
            (!fieldMapping.color ||
                `${fieldName}.${colorFieldName}` !== fields[fieldMapping.color].related);
        let rawColors = [];
        if (shouldFetchColor) {
            const relatedIds = rawFilters.map(({ id }) => id);
            if (relatedIds.length) {
                rawColors = await this.orm.searchRead(
                    field.relation,
                    [["id", "in", relatedIds]],
                    [colorFieldName]
                );
            }
        }

        const filters = rawFilters.map((rawFilter) => {
            const previousDynamicFilter = previousFilters.find(
                (f) => f.type === "dynamic" && f.value === rawFilter.id
            );
            return this.makeFilterDynamic(
                filterInfo,
                previousDynamicFilter,
                fieldName,
                rawFilter,
                rawColors
            );
        });

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
    /**
     * @protected
     */
    makeFilterDynamic(filterInfo, previousFilter, fieldName, rawFilter, rawColors) {
        const { fieldMapping, fields } = this.meta;
        const rawValue = rawFilter[fieldName];
        const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
        const field = fields[fieldName];
        const formatter = registry.category("formatters").get(field.type);

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
        if (rawColors.length) {
            const rawColor = rawColors.find(({ id }) => id === value);
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
    /**
     * @protected
     */
    makeFilterRecord(filterInfo, previousFilter, rawRecord) {
        const { colorFieldName, filterFieldName, writeFieldName } = filterInfo;
        const { fields, fieldMapping } = this.meta;
        const raw = rawRecord[writeFieldName];
        const value = Array.isArray(raw) ? raw[0] : raw;
        const field = fields[writeFieldName];
        const isX2Many = ["many2many", "one2many"].includes(field.type);
        const formatter = registry.category("formatters").get(isX2Many ? "many2one" : field.type);

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
    /**
     * @protected
     */
    makeFilterUser(filterInfo, previousFilter, fieldName, rawRecords) {
        const field = this.meta.fields[fieldName];
        const userFieldName = field.relation === "res.partner" ? "partnerId" : "userId";
        const value = user[userFieldName];

        let colorIndex = value;
        const rawRecord = rawRecords.find((r) => r[filterInfo.writeFieldName][0] === value);
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
