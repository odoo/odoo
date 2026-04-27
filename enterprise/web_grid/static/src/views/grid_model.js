/** @odoo-module */

import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { serializeDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { Model } from "@web/model/model";
import { browser } from "@web/core/browser/browser";

const { DateTime, Interval } = luxon;

export class GridCell {
    /**
     * Constructor
     *
     * @param dataPoint{GridDataPoint} the grid model.
     * @param row {GridRow} the grid row linked to the cell.
     * @param column {GridColumn} the grid column linked to the cell.
     * @param value {Number} the value of the cell.
     * @param isHovered {Boolean} is the cell in a hover state?
     */
    constructor(dataPoint, row, column, value = 0, isHovered = false) {
        this._dataPoint = dataPoint;
        this.row = row;
        this.column = column;
        this.model = dataPoint.model;
        this.value = value;
        this.isHovered = isHovered;
        this._readonly = false;
        this.column.addCell(this);
    }

    get readonly() {
        return this._readonly || this.column.readonly;
    }

    /**
     * Get the domain of the cell, it will be the domain of row AND the one of the column associated
     *
     * @return {Domain} the domain of the cell
     */
    get domain() {
        const domains = [this._dataPoint.searchParams.domain, this.row.domain, this.column.domain];
        return Domain.and(domains);
    }

    /**
     * Get the context to get the default values
     */
    get context() {
        return {
            ...(this.model.searchParams.context || {}),
            ...this.row.section?.context,
            ...this.row.context,
            ...this.column.context,
        };
    }

    get title() {
        const rowTitle = !this.row.section || this.row.section.isFake
            ? this.row.title
            : `${this.row.section.title} / ${this.row.title}`;
        const columnTitle = this.column.title;
        return `${rowTitle} (${columnTitle})`;
    }

    /**
     * Update the grid cell according to the value set by the current user.
     *
     * @param {Number} value the value entered by the current user.
     */
    async update(value) {
        return this.model.mutex.exec(async () => {
            await this._update(value);
        });
    }

    async _update(value) {
        const oldValue = this.value;
        const result = await this.model.orm.call(
            this.model.resModel,
            "grid_update_cell",
            [this.domain.toList({}), this.model.measureFieldName, value - oldValue],
            { context: this.context }
        );
        if (result) {
            this.model.actionService.doAction(result);
            return;
        }
        this.row.updateCell(this.column, value);
        this.model.notify();
    }
}

export class GridRow {
    /**
     * Constructor
     *
     * @param domain {Domain} the domain of the row.
     * @param valuePerFieldName {{string: string}} the list of to display the label of the row.
     * @param dataPoint {GridDataPoint} the grid model.
     * @param section {GridSection} the section of the grid.
     * @param columns {GridColumn[]} the columns of the grid.
     */
    constructor(domain, valuePerFieldName, dataPoint, section, isAdditionalRow = false) {
        this._domain = domain;
        this._dataPoint = dataPoint;
        this.cells = {};
        this.valuePerFieldName = valuePerFieldName;
        this.id = dataPoint.rowId++;
        this.model = dataPoint.model;
        this.section = section;
        if (section) {
            this.section.addRow(this);
        }
        this.grandTotal = 0;
        this.grandTotalWeekendHidden = 0;
        this.isAdditionalRow = isAdditionalRow;
        this._generateCells();
    }

    get initialRecordValues() {
        return this.valuePerFieldName;
    }

    get title() {
        const labelArray = [];
        for (const rowField of this._dataPoint.rowFields) {
            let title = this.valuePerFieldName[rowField.name];
            if (this.model.fieldsInfo[rowField.name].type === "many2one") {
                if (title) {
                    title = title[1];
                } else if (labelArray.length) {
                    title = "";
                } else {
                    title = "None";
                }
            }
            if (title) {
                labelArray.push(title);
            }
        }
        return labelArray.join(" / ");
    }

    get domain() {
        if (this.section.isFake) {
            return this._domain;
        }
        return Domain.and([this.section.domain, this._domain]);
    }

    get context() {
        const context = {};
        const getValue = (fieldName, value) =>
            this.model.fieldsInfo[fieldName].type === "many2one" ? value && value[0] : value;
        for (const [key, value] of Object.entries(this.valuePerFieldName)) {
            context[`default_${key}`] = getValue(key, value);
        }
        return context;
    }

    getSection() {
        return !this.section.isFake && this.section;
    }

    /**
     * Generate the cells for each column that is present in the row.
     * @private
     */
    _generateCells() {
        for (const column of this._dataPoint.columnsArray) {
            this.cells[column.id] = new this.model.constructor.Cell(
                this._dataPoint,
                this,
                column,
                0
            );
        }
    }

    _ensureColumnExist(column) {
        if (!(column.id in this._dataPoint.data.columns)) {
            throw new Error("Unbound index: the columnId is not in the row columns");
        }
        return true;
    }

    /**
     * Update the cell value of a cell.
     * @param {GridColumn} column containing the cell to update.
     * @param {number} value the value to update
     */
    updateCell(column, value) {
        this._ensureColumnExist(column);
        const cell = this.cells[column.id];
        const oldValue = cell.value;
        cell.value = value;
        const delta = value - oldValue;
        this.section.updateGrandTotal(column, delta);
        this.grandTotal += delta;
        this.grandTotalWeekendHidden += column.isWeekDay ? delta : 0;
        column.grandTotal += delta;
        if (this.isAdditionalRow && delta > 0) {
            this.isAdditionalRow = false;
        }
    }

    setReadonlyCell(column, readonly) {
        this._ensureColumnExist(column);
        if (readonly instanceof Array) {
            readonly = readonly.length > 0;
        } else if (!(readonly instanceof Boolean)) {
            readonly = Boolean(readonly);
        }
        this.cells[column.id]._readonly = readonly;
    }

    getGrandTotal(showWeekend) {
        return showWeekend ? this.grandTotal : this.grandTotalWeekendHidden;
    }
}

export class GridSection extends GridRow {
    constructor() {
        super(...arguments);
        this.sectionId = this._dataPoint.sectionId++;
        this.rows = {};
        this.isSection = true;
        this.lastRow = null;
    }

    get value() {
        return this.valuePerFieldName && this.valuePerFieldName[this._dataPoint.sectionField.name];
    }

    get domain() {
        let value = this.value;
        if (this.model.fieldsInfo[this._dataPoint.sectionField.name].type === "many2one") {
            value = value && value[0];
        }
        return new Domain([[this._dataPoint.sectionField.name, "=", value]]);
    }

    get title() {
        let title = this.value;
        if (
            this._dataPoint.sectionField &&
            this._dataPoint.fieldsInfo[this._dataPoint.sectionField.name].type === "many2one"
        ) {
            title = (title && title[1]) || "None";
        }
        return title;
    }

    get initialRecordValues() {
        return { [this._dataPoint.sectionField.name]: this.value };
    }

    get isFake() {
        return this.value == null;
    }

    get context() {
        const context = {};
        const getValue = (fieldName, value) =>
            this.model.fieldsInfo[fieldName].type === "many2one" ? value && value[0] : value;

        if (!this.isFake) {
            const sectionFieldName = this._dataPoint.sectionField.name;
            context[`default_${sectionFieldName}`] = getValue(sectionFieldName, this.value);
        }
        return context;
    }

    getSection() {
        return !this.isFake && this;
    }

    /**
     * Add row to the section rows.
     * @param row {GridRow} the row to add.
     */
    addRow(row) {
        if (row.id in this.rows) {
            throw new Error("Row already added in section");
        }
        this.rows[row.id] = row;
        this.lastRow = row;
    }

    /**
     * Update the grand totals according to the provided column and delta.
     * @param column {GridColumn} the column the grand total has to be updated for.
     * @param delta {Number} the delta to apply on the grand totals.
     */
    updateGrandTotal(column, delta) {
        this.cells[column.id].value += delta;
        this.grandTotal += delta;
        this.grandTotalWeekendHidden += column.isWeekDay ? delta : 0;
    }
}

export class GridColumn {
    /**
     * Constructor
     *
     * @param dataPoint {GridDataPoint} dataPoint of the grid.
     * @param title {string} the title of the column to display.
     */
    constructor(dataPoint, title, value, readonly = false) {
        this._dataPoint = dataPoint;
        this.model = dataPoint.model;
        this.title = title;
        this.value = value;
        this.cells = [];
        this.id = dataPoint.columnId++;
        this.grandTotal = 0;
        this.readonly = readonly;
    }

    /**
     * Add the cell to the column cells.
     * @param cell {GridCell} the cell to add.
     */
    addCell(cell) {
        if (cell.id in this.cells) {
            throw new Error("Cell already added in column");
        }
        this.cells.push(cell);
        this.grandTotal += cell.value;
    }

    get domain() {
        return new Domain([[this._dataPoint.columnFieldName, "=", this.value]]);
    }

    get context() {
        return { [`default_${this._dataPoint.columnFieldName}`]: this.value };
    }
}

export class DateGridColumn extends GridColumn {
    /**
     * Constructor
     *
     * @param dataPoint {GridDataPoint} data point of the grid.
     * @param title {string} the title of the column to display.
     * @param dateStart {String} the date start serialized
     * @param dateEnd {String} the date end serialized
     * @param isToday {Boolean} is the date column representing today?
     */
    constructor(dataPoint, title, dateStart, dateEnd, isToday, isWeekDay, readonly = false) {
        super(dataPoint, title, dateStart, readonly);
        this.dateEnd = dateEnd;
        this.isToday = isToday;
        this.isWeekDay = isWeekDay;
    }

    get domain() {
        return new Domain([
            "&",
            [this._dataPoint.columnFieldName, ">=", this.value],
            [this._dataPoint.columnFieldName, "<", this.dateEnd],
        ]);
    }
}

export class GridDataPoint {
    constructor(model, params) {
        this.model = model;
        const { rowFields, sectionField, searchParams } = params;
        this.rowFields = rowFields;
        this.sectionField = sectionField;
        this.searchParams = searchParams;
        this.sectionId = 0;
        this.rowId = 0;
        this.columnId = 0;
    }

    get orm() {
        return this.model.orm;
    }

    get Section() {
        return this.model.constructor.Section;
    }

    get Row() {
        return this.model.constructor.Row;
    }

    get Column() {
        return this.model.constructor.Column;
    }

    get DateColumn() {
        return this.model.constructor.DateColumn;
    }

    get Cell() {
        return this.model.constructor.Cell;
    }

    get fieldsInfo() {
        return this.model.fieldsInfo;
    }

    get columnFieldName() {
        return this.model.columnFieldName;
    }

    get resModel() {
        return this.model.resModel;
    }

    get fields() {
        return this._getFields();
    }

    get groupByFields() {
        return this._getFields(true);
    }

    get navigationInfo() {
        return this.model.navigationInfo;
    }

    get dateFormat() {
        return { day: "ccc,\nMMM\u00A0d", month: "MMMM\nyyyy" };
    }

    get columnFieldIsDate() {
        return this.model.columnFieldIsDate;
    }

    get columnGroupByFieldName() {
        let columnGroupByFieldName = this.columnFieldName;
        if (this.columnFieldIsDate) {
            columnGroupByFieldName += `:${this.navigationInfo.range.step}`;
        }
        return columnGroupByFieldName;
    }

    get readonlyField() {
        return this.model.readonlyField;
    }

    get sectionsArray() {
        return Object.values(this.data.sections);
    }

    get rowsArray() {
        return Object.values(this.data.rows);
    }

    get columnsArray() {
        return Object.values(this.data.columns);
    }

    /**
     * Get fields to use in the group by or in fields of the read_group
     * @private
     * @param grouped true to return the fields for the group by.
     * @return {string[]} list of fields name.
     */
    _getFields(grouped = false) {
        const fields = [];
        if (!grouped) {
            fields.push(
                this.columnFieldName,
                this.model.measureGroupByFieldName,
                "ids:array_agg(id)"
            );
            if (this.readonlyField) {
                const aggReadonlyField = `${this.readonlyField.name}:${this.readonlyField.aggregator}`;
                fields.push(aggReadonlyField);
            }
        } else {
            fields.push(this.columnGroupByFieldName);
        }
        fields.push(...this.rowFields.map((r) => r.name));
        if (this.sectionField) {
            fields.push(this.sectionField.name);
        }
        return fields;
    }

    _getDateColumnTitle(date) {
        if (this.navigationInfo.range.step in this.dateFormat) {
            return date.toFormat(this.dateFormat[this.navigationInfo.range.step]);
        }
        return serializeDate(date);
    }

    /**
     * Generate the date columns.
     * @private
     * @return {GridColumn[]}
     */
    _generateDateColumns() {
        const generateNext = (dateStart) =>
            dateStart.plus({ [`${this.navigationInfo.range.step}s`]: 1 });
        for (
            let currentDate = this.navigationInfo.periodStart;
            currentDate < this.navigationInfo.periodEnd;
            currentDate = generateNext(currentDate)
        ) {
            const domainStart = currentDate;
            const domainStop = generateNext(currentDate);
            const domainStartSerialized = serializeDate(domainStart);
            const isWeekDay = currentDate.weekday < 6;
            const column = new this.DateColumn(
                this,
                this._getDateColumnTitle(currentDate),
                domainStartSerialized,
                serializeDate(domainStop),
                currentDate.startOf("day").equals(this.model.today.startOf("day")),
                isWeekDay,
            );
            this.data.columns[column.id] = column;
            this.data.columnsKeyToIdMapping[domainStartSerialized] = column.id;
        }
    }

    /**
     * Search grid columns
     *
     * @param {Array} domain domain to filter the result
     * @param {string} readonlyField field uses to make column readonly if true
     * @returns {Array} array containing id, display_name and readonly if readonlyField is defined.
     */
    async _searchMany2oneColumns(domain, readonlyField) {
        const fieldsToFetch = ["id", "display_name"];
        if (readonlyField) {
            fieldsToFetch.push(readonlyField);
        }
        const columnField = this.fieldsInfo[this.columnFieldName];
        const columnRecords = await this.orm.searchRead(
            columnField.relation,
            domain || [],
            fieldsToFetch
        );
        return columnRecords.map((read) => Object.values(read));
    }

    /**
     * Initialize the data.
     * @private
     */
    async _initialiseData() {
        this.data = {
            columnsKeyToIdMapping: {},
            columns: {},
            rows: {},
            rowsKeyToIdMapping: {},
            fieldsInfo: this.fieldsInfo,
            sections: {},
            sectionsKeyToIdMapping: {},
        };
        this.record = {
            context: {},
            resModel: this.resModel,
            resIds: [],
        };
        let columnRecords = [];
        const columnField = this.fieldsInfo[this.columnFieldName];
        if (this.columnFieldIsDate) {
            this._generateDateColumns();
        } else {
            if (columnField.type === "selection") {
                const selectionFieldValues = await this.orm.call(
                    "ir.model.fields",
                    "get_field_selection",
                    [this.resModel, this.columnFieldName]
                );
                columnRecords = selectionFieldValues;
            } else if (columnField.type === "many2one") {
                columnRecords = await this._searchMany2oneColumns();
            } else {
                throw new Error(
                    "Unmanaged column type. Supported types are date, selection and many2one."
                );
            }
            for (const record of columnRecords) {
                let readonly = false;
                let key, value;
                if (record.length === 2) {
                    [key, value] = record;
                } else {
                    [key, value, readonly] = record;
                }
                const column = new this.Column(this, value, key, Boolean(readonly));
                this.data.columns[column.id] = column;
                this.data.columnsKeyToIdMapping[key] = column.id;
            }
        }
    }

    async fetchData() {
        const data = await this.orm.webReadGroup(
            this.resModel,
            Domain.and([this.searchParams.domain, this.model.generateNavigationDomain()]).toList(
                {}
            ),
            this.fields,
            this.groupByFields,
            {
                lazy: false,
            }
        );
        if (this.orm.isSample) {
            data.groups = data.groups.filter((group) => {
                const date = DateTime.fromISO(group["__range"][this.columnGroupByFieldName].from);
                return (
                    date >= this.navigationInfo.periodStart && date <= this.navigationInfo.periodEnd
                );
            });
        }
        return data;
    }

    /**
     * Gets additional groups to be added to the grid. The call to this function is made in parallel to the main data
     * fetching.
     *
     * This function is intended to be overriden in modules where we want to display additional sections and/or rows in
     * the grid than what would be returned by the webReadGroup.
     * The model `sectionField` and `rowFields` can be used in order to know what need to be returned.
     *
     * An example of this is:
     * - when considering timesheet, we want to ease their encoding by adding (to the data that is fetched for scale),
     *   the entries that have been entered the week before. That way, the first day of week
     *   (or month, depending on the scale), a line is already displayed with 0's and can directly been used in the
     *   grid instead of having to use the create button.
     *
     * @return {Array<Promise<Object>>} an array of Promise of Object of type:
     *                                      {
     *                                          sectionKey: {
     *                                              value: Any,
     *                                              rows: {
     *                                                  rowKey: {
     *                                                      domain: Domain,
     *                                                      values: [Any],
     *                                                  },
     *                                              },
     *                                          },
     *                                      }
     * @private
     */
    _fetchAdditionalData() {
        return [];
    }

    /**
     * Gets additional groups to be added to the grid. The call to this function is made after the main data fetching
     * has been processed which allows using `data` in the code.
     * This function is intended to be overriden in modules where we want to display additional sections and/or rows in
     * the grid than what would be returned by the webReadGroup.
     * The model `sectionField`, `rowFields` as well as `data` can be used in order to know what need to be returned.
     *
     * @return {Array<Promise<Object>>} an array of Promise of Object of type:
     *                                      {
     *                                          sectionKey: {
     *                                              value: Any,
     *                                              rows: {
     *                                                  rowKey: {
     *                                                      domain: Domain,
     *                                                      values: [Any],
     *                                                  },
     *                                              },
     *                                          },
     *                                      }
     * @private
     */
    _postFetchAdditionalData() {
        return [];
    }

    _getAdditionalPromises() {
        return [this._fetchUnavailabilityDays()];
    }

    async _fetchUnavailabilityDays(args = {}) {
        if (!this.columnFieldIsDate) {
            return {};
        }
        const result = await this.orm.call(
            this.resModel,
            "grid_unavailability",
            [
                serializeDate(this.navigationInfo.periodStart),
                serializeDate(this.navigationInfo.periodEnd),
            ],
            {
                ...args,
            }
        );
        this._processUnavailabilityDays(result);
    }

    _processUnavailabilityDays(result) {
        return;
    }

    /**
     * Generate the row key according to the provided read group result.
     * @param readGroupResult {Array} the read group result the key has to be generated for.
     * @private
     * @return {string}
     */
    _generateRowKey(readGroupResult) {
        let key = "";
        const sectionKey =
            (this.sectionField && this._generateSectionKey(readGroupResult)) || false;
        for (const rowField of this.rowFields) {
            let value = rowField.name in readGroupResult && readGroupResult[rowField.name];
            if (this.fieldsInfo[rowField.name].type === "many2one") {
                value = value && value[0];
            }
            key += `${value}\\|/`;
        }
        return `${sectionKey}@|@${key}`;
    }

    /**
     * Generate the section
     * @param readGroupResult
     * @private
     */
    _generateSectionKey(readGroupResult) {
        let value = readGroupResult[this.sectionField.name];
        if (this.fieldsInfo[this.sectionField.name].type === "many2one") {
            value = value && value[0];
        }
        return `/|\\${value.toString()}`;
    }

    /**
     * Generate the row domain for the provided read group result.
     * @param readGroupResult {Array} the read group result the domain has to be generated for.
     * @return {{domain: Domain, values: Object}} the generated domain and values.
     */
    _generateRowDomainAndValues(readGroupResult) {
        let domain = new Domain();
        const values = {};
        for (const rowField of this.rowFields) {
            const result = rowField.name in readGroupResult && readGroupResult[rowField.name];
            let value = result;
            if (this.fieldsInfo[rowField.name].type === "many2one") {
                value = value && value[0];
            }
            values[rowField.name] = result;
            domain = Domain.and([domain, [[rowField.name, "=", value]]]);
        }
        return { domain, values };
    }

    _generateFakeSection() {
        const section = new this.Section(null, null, this, null);
        this.data.sections[section.id] = section;
        this.data.sectionsKeyToIdMapping["false"] = section.id;
        this.data.rows[section.id] = section;
        this.data.rowsKeyToIdMapping["false"] = section.id;
        return section;
    }

    async _generateData(readGroupResults) {
        let section;
        for (const readGroupResult of readGroupResults.groups) {
            if (!this.orm.isSample) {
                this.record.resIds.push(...readGroupResult.ids);
            }
            const rowKey = this._generateRowKey(readGroupResult);
            if (this.sectionField) {
                const sectionKey = this._generateSectionKey(readGroupResult);
                if (!(sectionKey in this.data.sectionsKeyToIdMapping)) {
                    const newSection = new this.Section(
                        null,
                        { [this.sectionField.name]: readGroupResult[this.sectionField.name] },
                        this,
                        null
                    );
                    this.data.sections[newSection.id] = newSection;
                    this.data.sectionsKeyToIdMapping[sectionKey] = newSection.id;
                    this.data.rows[newSection.id] = newSection;
                    this.data.rowsKeyToIdMapping[sectionKey] = newSection.id;
                }
                section = this.data.sections[this.data.sectionsKeyToIdMapping[sectionKey]];
            } else if (Object.keys(this.data.sections).length === 0) {
                section = this._generateFakeSection();
            }
            let row;
            if (!(rowKey in this.data.rowsKeyToIdMapping)) {
                const { domain, values } = this._generateRowDomainAndValues(readGroupResult);
                row = new this.Row(domain, values, this, section);
                this.data.rows[row.id] = row;
                this.data.rowsKeyToIdMapping[rowKey] = row.id;
            } else {
                row = this.data.rows[this.data.rowsKeyToIdMapping[rowKey]];
            }
            let columnKey;
            if (this.columnFieldIsDate) {
                columnKey = readGroupResult["__range"][this.columnGroupByFieldName].from;
            } else {
                const columnField = this.fieldsInfo[this.columnFieldName];
                if (columnField.type === "selection") {
                    columnKey = readGroupResult[this.columnFieldName];
                } else if (columnField.type === "many2one") {
                    columnKey = readGroupResult[this.columnFieldName][0];
                } else {
                    throw new Error(
                        "Unmanaged column type. Supported types are date, selection and many2one."
                    );
                }
            }
            if (this.data.columnsKeyToIdMapping[columnKey] in this.data.columns) {
                const column = this.data.columns[this.data.columnsKeyToIdMapping[columnKey]];
                row.updateCell(column, readGroupResult[this.model.measureFieldName]);
                if (this.readonlyField && this.readonlyField.name in readGroupResult) {
                    row.setReadonlyCell(column, readGroupResult[this.readonlyField.name]);
                }
            }
        }
    }

    /**
     * Method meant to be overridden whenever an item (row and section) post process is needed.
     * @param item {GridSection|GridRow}
     */
    _itemsPostProcess(item) {}

    async load() {
        await this._initialiseData();

        const mergeAdditionalData = (fetchedData) => {
            const additionalData = {};
            for (const data of fetchedData) {
                for (const [sectionKey, sectionInfo] of Object.entries(data)) {
                    if (!(sectionKey in additionalData)) {
                        additionalData[sectionKey] = sectionInfo;
                    } else {
                        for (const [rowKey, rowInfo] of Object.entries(sectionInfo.rows)) {
                            if (!(rowKey in additionalData[sectionKey].rows)) {
                                additionalData[sectionKey].rows[rowKey] = rowInfo;
                            }
                        }
                    }
                }
            }
            return additionalData;
        };

        const appendAdditionData = (additionalData) => {
            for (const [sectionKey, sectionInfo] of Object.entries(additionalData)) {
                if (!(sectionKey in this.data.sectionsKeyToIdMapping)) {
                    if (this.sectionField) {
                        const newSection = new this.Section(
                            null,
                            { [this.sectionField.name]: sectionInfo.value },
                            this,
                            null
                        );
                        this.data.sections[newSection.id] = newSection;
                        this.data.sectionsKeyToIdMapping[sectionKey] = newSection.id;
                        this.data.rows[newSection.id] = newSection;
                        this.data.rowsKeyToIdMapping[sectionKey] = newSection.id;
                    } else {
                        // if no sectionField and the section is not in sectionsKeyToIdMapping then no section is generated
                        this._generateFakeSection();
                    }
                }
                const section = this.data.sections[this.data.sectionsKeyToIdMapping[sectionKey]];
                for (const [rowKey, rowInfo] of Object.entries(sectionInfo.rows)) {
                    if (!(rowKey in this.data.rowsKeyToIdMapping)) {
                        const newRow = new this.Row(
                            rowInfo.domain,
                            rowInfo.values,
                            this,
                            section,
                            true
                        );
                        this.data.rows[newRow.id] = newRow;
                        this.data.rowsKeyToIdMapping[rowKey] = newRow.id;
                        for (const column of Object.values(this.data.columns)) {
                            newRow.updateCell(column, 0);
                        }
                    }
                }
            }
        };

        const [data, additionalData] = await Promise.all([
            this.fetchData(),
            Promise.all(this._fetchAdditionalData()),
        ]);
        this._generateData(data);
        appendAdditionData(mergeAdditionalData(additionalData));
        if (!this.orm.isSample) {
            const [, postFetchAdditionalData] = await Promise.all([
                Promise.all(this._getAdditionalPromises()),
                Promise.all(this._postFetchAdditionalData()),
            ]);
            appendAdditionData(mergeAdditionalData(postFetchAdditionalData));
        }

        this.data.items = [];
        for (const section of this.sectionsArray) {
            this.data.items.push(section);
            this._itemsPostProcess(section);
            for (const rowId in section.rows) {
                const row = section.rows[rowId];
                this._itemsPostProcess(row);
                this.data.items.push(row);
            }
        }
    }
}

export class GridNavigationInfo {
    constructor(anchor, model) {
        this.anchor = anchor;
        this.model = model;
    }

    get _targetWeekday() {
        const firstDayOfWeek = localization.weekStart;
        return this.anchor.weekday < firstDayOfWeek ? firstDayOfWeek - 7 : firstDayOfWeek;
    }

    get periodStart() {
        if (this.range.span !== "week") {
            return this.anchor.startOf(this.range.span);
        }
        // Luxon's default is monday to monday week so we need to change its behavior.
        return this.anchor.set({ weekday: this._targetWeekday }).startOf("day");
    }

    get periodEnd() {
        if (this.range.span !== "week") {
            return this.anchor.endOf(this.range.span);
        }
        // Luxon's default is monday to monday week so we need to change its behavior.
        return this.anchor
            .set({ weekday: this._targetWeekday })
            .plus({ weeks: 1, days: -1 })
            .endOf("day");
    }

    get interval() {
        return Interval.fromDateTimes(this.periodStart, this.periodEnd);
    }

    contains(date) {
        return this.interval.contains(date.startOf("day"));
    }
}

export class GridModel extends Model {
    static DataPoint = GridDataPoint;
    static Cell = GridCell;
    static Column = GridColumn;
    static DateColumn = DateGridColumn;
    static Row = GridRow;
    static Section = GridSection;
    static NavigationInfo = GridNavigationInfo;

    setup(params) {
        this.notificationService = useService("notification");
        this.actionService = useService("action");
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();
        this.defaultSectionField = params.sectionField;
        this.defaultRowFields = params.rowFields;
        this.resModel = params.resModel;
        this.fieldsInfo = params.fieldsInfo;
        this.columnFieldName = params.columnFieldName;
        this.columnFieldIsDate = this.fieldsInfo[params.columnFieldName].type === "date";
        this.measureField = params.measureField;
        this.readonlyField = params.readonlyField;
        this.ranges = params.ranges;
        this.defaultAnchor = params.defaultAnchor || this.today;
        this.navigationInfo = new this.constructor.NavigationInfo(this.defaultAnchor, this);
        const activeRangeName =
            browser.localStorage.getItem(this.storageKey) || params.activeRangeName;
        if (Object.keys(this.ranges).length && activeRangeName) {
            this.navigationInfo.range = this.ranges[activeRangeName];
        }
    }

    get data() {
        return this._dataPoint?.data || {};
    }

    get record() {
        return this._dataPoint?.record || {};
    }

    get today() {
        return DateTime.local().startOf("day");
    }

    get sectionsArray() {
        return Object.values(this.data.sections);
    }

    get itemsArray() {
        return this.data.items;
    }

    get columnsArray() {
        return Object.values(this.data.columns);
    }

    get maxColumnsTotal() {
        return Math.max(...this.columnsArray.map((c) => c.grandTotal));
    }

    get measureFieldName() {
        return this.measureField.name;
    }

    get measureGroupByFieldName() {
        if (this.measureField.aggregator) {
            return `${this.measureFieldName}:${this.measureField.aggregator}`;
        }
        return this.measureFieldName;
    }

    get storageKey() {
        return `scaleOf-viewId-${this.env.config.viewId}`;
    }

    isToday(date) {
        return date.startOf("day").equals(this.today.startOf("day"));
    }

    /**
     * Set the new range according to the range name passed into parameter.
     * @param rangeName {string} the range name to set.
     */
    async setRange(rangeName) {
        this.navigationInfo.range = this.ranges[rangeName];
        browser.localStorage.setItem(this.storageKey, rangeName);
        await this.fetchData();
    }

    async setAnchor(anchor) {
        this.navigationInfo.anchor = anchor;
        await this.fetchData();
    }

    async setTodayAnchor() {
        await this.setAnchor(this.today);
    }

    /**
     * @override
     */
    hasData() {
        return this.sectionsArray.length;
    }

    generateNavigationDomain() {
        if (this.columnFieldIsDate) {
            return new Domain([
                "&",
                [this.columnFieldName, ">=", serializeDate(this.navigationInfo.periodStart)],
                [this.columnFieldName, "<=", serializeDate(this.navigationInfo.periodEnd)],
            ]);
        } else {
            return Domain.TRUE;
        }
    }

    /**
     * Reset the anchor
     */
    async resetAnchor() {
        await this.setAnchor(this.defaultAnchor);
    }

    /**
     * Move the anchor to the next/previous step
     * @param direction {"forward"|"backward"} the direction to the move the anchor
     */
    async moveAnchor(direction) {
        if (direction == "forward") {
            this.navigationInfo.anchor = this.navigationInfo.anchor.plus({
                [this.navigationInfo.range.span]: 1,
            });
        } else if (direction == "backward") {
            this.navigationInfo.anchor = this.navigationInfo.anchor.minus({
                [this.navigationInfo.range.span]: 1,
            });
        } else {
            throw Error("Invalid argument");
        }
        if (
            this.navigationInfo.contains(this.today) &&
            this.navigationInfo.anchor.startOf("day").equals(this.today.startOf("day"))
        ) {
            this.navigationInfo.anchor = this.today;
        }
        await this.fetchData();
    }

    /**
     * Load the model
     *
     * @override
     * @param params {Object} the search parameters (domain, groupBy, etc.)
     * @return {Promise<void>}
     */
    async load(params = {}) {
        const searchParams = {
            ...this.searchParams,
            ...params,
        };
        const groupBys = [];
        let notificationDisplayed = false;
        for (const groupBy of searchParams.groupBy) {
            if (groupBy.startsWith(this.columnFieldName)) {
                if (!notificationDisplayed) {
                    this.notificationService.add(
                        _t(
                            "Grouping by the field used in the column of the grid view is not possible."
                        ),
                        { type: "warning" }
                    );
                    notificationDisplayed = true;
                }
            } else {
                groupBys.push(groupBy);
            }
        }
        if (searchParams.length !== groupBys.length) {
            searchParams.groupBy = groupBys;
        }
        let rowFields = [];
        let sectionField;
        if (searchParams.groupBy.length) {
            if (
                this.defaultSectionField &&
                searchParams.groupBy.length > 1 &&
                searchParams.groupBy[0] === this.defaultSectionField.name
            ) {
                sectionField = this.defaultSectionField;
            }
            const rowFieldPerFieldName = Object.fromEntries(
                this.defaultRowFields.map((r) => [r.name, r])
            );
            for (const groupBy of searchParams.groupBy) {
                if (sectionField && groupBy === sectionField.name) {
                    continue;
                }
                if (groupBy in rowFieldPerFieldName) {
                    rowFields.push({
                        ...rowFieldPerFieldName[groupBy],
                        invisible: "False",
                    });
                } else {
                    rowFields.push({ name: groupBy });
                }
            }
        } else {
            if (this.defaultSectionField && (this.defaultSectionField.invisible !== "True" && this.defaultSectionField.invisible !== "1")) {
                sectionField = this.defaultSectionField;
            }
            rowFields = this.defaultRowFields.filter((r) => (r.invisible !== "True" && r.invisible !== "1"));
        }

        const dataPoint = new this.constructor.DataPoint(this, {
            searchParams,
            rowFields,
            sectionField,
        });
        await this.keepLast.add(dataPoint.load());
        this._dataPoint = dataPoint;

        this.searchParams = searchParams;
        this.rowFields = rowFields;
        this.sectionField = sectionField;
    }

    async fetchData(params = {}) {
        await this.load(params);
        this.useSampleModel = false;
        this.notify();
    }
}
