/** @odoo-module */

import { serializeDate } from "@web/core/l10n/dates";
import { GridDataPoint, GridModel } from "@web_grid/views/grid_model";
import { Domain } from "@web/core/domain";

export class TimesheetGridDataPoint extends GridDataPoint {
    async load() {
        this.unavailabilityDaysPerEmployeeId = {};
        await super.load();
        if (!this.orm.isSample) {
            await Promise.all(this.timesheetWorkingHoursPromises);
        }
    }

    _sortGridRows(data) {
        const orderFieldArray = this.rowFields.map((rowField) => this.fieldsInfo[rowField.name]);
        if (this.sectionField) {
            orderFieldArray.unshift(this.fieldsInfo[this.sectionField.name]);
        }
        data.groups = data.groups.sort((firstRow, secondRow) => {
            for (const orderField of orderFieldArray) {
                const fieldName = orderField.name;
                let firstRowFieldData = firstRow[fieldName];
                let secondRowFieldData = secondRow[fieldName];
                if (orderField.type === "many2one") {
                    firstRowFieldData = firstRowFieldData[1];
                    secondRowFieldData = secondRowFieldData[1];
                } else if (orderField.type === "selection") {
                    firstRowFieldData =
                        firstRowFieldData in orderField.selection
                            ? orderField.selection[firstRowFieldData]
                            : firstRowFieldData;
                    secondRowFieldData =
                        secondRowFieldData in orderField.selection
                            ? orderField.selection[secondRowFieldData]
                            : secondRowFieldData;
                 }
                if (firstRowFieldData === secondRowFieldData) {
                    continue;
                }
                if (!firstRowFieldData) {
                    return -1;
                }
                if (!secondRowFieldData) {
                    return 1;
                }
                return firstRowFieldData
                    .toLowerCase()
                    .localeCompare(secondRowFieldData.toLowerCase());
                }
            return 0;
        });
    }

    async fetchData() {
        const data = await super.fetchData();
        this._sortGridRows(data);
        return data;
    }

    get timesheetWorkingHoursPromises() {
        return [
            this._fetchWorkingHoursData("task_id"),
            this._fetchWorkingHoursData("project_id"),
            this._fetchAllTimesheetM2OAvatarData(),
        ];
    }

    async _initialiseData() {
        await super._initialiseData();
        this.data.workingHours = {};
    }

    _getFavoriteTaskDomain() {
        return [
            ["project_id", "!=", false],
            ["user_ids", "in", this.searchParams.context.uid],
            ["allow_timesheets", "=", true],
            ["planned_date_begin", "<=", serializeDate(this.navigationInfo.periodEnd)],
            ["date_deadline", ">=", serializeDate(this.navigationInfo.periodStart)],
        ];
    }

    _getPreviousWeekTimesheetDomain() {
        return [
            [
                this.columnFieldName,
                ">=",
                serializeDate(this.navigationInfo.periodStart.minus({ weeks: 1 })),
            ],
            [this.columnFieldName, "<", serializeDate(this.navigationInfo.periodStart)],
        ];
    }

    /**
     * @override
     */
    _fetchAdditionalData() {
        const additionalGroups = super._fetchAdditionalData();
        if (!this.searchParams.context.group_expand || this.navigationInfo.periodEnd <= this.model.today) {
            return additionalGroups;
        }

        const previouslyTimesheetedDomain = this._getPreviousWeekTimesheetDomain();

        const previouslyWeekTimesheet = this.orm
            .webReadGroup(
                this.resModel,
                Domain.and([this.searchParams.domain, previouslyTimesheetedDomain]).toList({}),
                this.fields,
                this.groupByFields,
                { lazy: false }
            )
            .then((readGroupResults) => {
                const additionalData = {};
                this._sortGridRows(readGroupResults);
                for (const readGroupResult of readGroupResults.groups) {
                    let sectionKey = false;
                    let sectionValue = null;
                    if (this.sectionField) {
                        sectionKey = this._generateSectionKey(readGroupResult);
                        sectionValue = readGroupResult[this.sectionField.name];
                    }
                    const rowKey = this._generateRowKey(readGroupResult);
                    const { domain, values } = this._generateRowDomainAndValues(readGroupResult);
                    if (!(sectionKey in additionalData)) {
                        additionalData[sectionKey] = {
                            value: sectionValue,
                            rows: {},
                        };
                    }
                    if (!(rowKey in additionalData[sectionKey].rows)) {
                        additionalData[sectionKey].rows[rowKey] = {
                            domain: domain,
                            values,
                        };
                    }
                }
                return additionalData;
            });

        additionalGroups.push(previouslyWeekTimesheet);
        return additionalGroups;
    }

    _fetchUnavailabilityDays(args = {}) {
        const employeeIds = [];
        let groupByEmployee = false;
        if (this.columnFieldIsDate) {
            if (this.sectionField && this.sectionField.name === "employee_id") {
                groupByEmployee = true;
                for (const section of this.sectionsArray) {
                    if (section.value) {
                        employeeIds.push(section.value[0]);
                    }
                }
            } else if (this.rowFields.some((r) => r.name === "employee_id")) {
                groupByEmployee = true;
                for (const row of this.rowsArray) {
                    if (row.valuePerFieldName && row.valuePerFieldName.employee_id) {
                        employeeIds.push(row.valuePerFieldName.employee_id[0]);
                    }
                }
            }
        }
        return super._fetchUnavailabilityDays({
            res_ids: employeeIds,
            groupby: groupByEmployee ? "employee_id" : "",
        });
    }

    _processUnavailabilityDays(result) {
        this.unavailabilityDaysPerEmployeeId = result;
    }

    /**
     *
     * @override
     */
    _postFetchAdditionalData() {
        const additionalGroups = super._postFetchAdditionalData();

        if (!this.searchParams.context.group_expand) {
            return additionalGroups;
        }

        /*
         * The goal of this code is to add records in the grid in order to ease encoding.
         * We will add entries if 'task_id' or 'project_id' has been explicitly added to the domain from
         * the search view.
         */

        /*
         * First go through the domain in order to:
         * - Check that 'task_id' and 'project_id' are present in the domain (except for "('project_id', '!=', false)")
         * - Build the list of fields, other than 'task_id' and 'project_id' that are used in the domain, in order to
         *   later be able to neutralise de leaf part of the domain that are applied on those fields.
         */
        const domainFieldsToNeutralize = [];
        let isProjectIdInDomainFields = false;
        let isTaskIdInDomainFields = false;
        let previousOperator = "&";
        let searchParamsDomain = [];
        for (const domainLeaf of new Domain(this.searchParams.domain).toList({})) {
            if (domainLeaf.length === 3) {
                const [fieldName, operator, value] = domainLeaf;
                if (fieldName === "project_id") {
                    if (!(operator === "!=" && value === false)) {
                        isProjectIdInDomainFields = true;
                    }
                } else if (fieldName === "task_id") {
                    isTaskIdInDomainFields = true;
                } else {
                    domainFieldsToNeutralize.push(fieldName);
                }
            } else {
                previousOperator = domainLeaf;
            }
            searchParamsDomain.push(domainLeaf);
        }
        searchParamsDomain = new Domain(searchParamsDomain);

        /*
         * If none of 'project_id' and 'task_id' are used as the section field or if none of 'project_id' and 'task_id'
         * are used in the search domain, return and don't perform the extra search.
         */
        const fieldsToConsider = ["project_id", "task_id"];
        const isProjectOrTaskAsSectionField =
            this.sectionField && fieldsToConsider.includes(this.sectionField.name);
        const isProjectOrTaskInRows = this.rowFields.some((field) =>
            fieldsToConsider.includes(field.name)
        );
        if (
            !(this.rowFields.some((field) => field.name === 'task_id') || (
                (isProjectOrTaskAsSectionField || isProjectOrTaskInRows) &&
                (isProjectIdInDomainFields || isTaskIdInDomainFields)
            ))
        ) {
            return additionalGroups;
        }

        // Neutralize other fields than 'project_id' and 'task_id' on the domain.
        const neutralizedDomain = Domain.removeDomainLeaves(
            searchParamsDomain,
            domainFieldsToNeutralize
        );

        /*
         * Go over the domain and create separated 'project_id' and 'task_id' domains. Replace 'project_id' and
         * 'task_id' by 'id' whenever applicable.
         * Don't add ('project_id', '!=', false) to the domain that will be executed on 'project.project', which is
         * there from the action in order to only select timesheets from the `account.account_move_line`. This domain
         * is however being preserved for task in order not to fetch private ones.
         */
        let taskDomain = [];
        let projectDomain = [];
        const getIdOrName = (fieldName, operator, value) => {
            if (
                ["ilike", "not ilike"].includes(operator) ||
                (["=", "!="].includes(operator) && typeof value === "string")
            ) {
                return "name";
            }
            return "id";
        };
        const getFieldDomain = (expectedFieldName, fieldName, operator, value) => {
            return [
                fieldName === expectedFieldName
                    ? getIdOrName(fieldName, operator, value)
                    : fieldName,
                operator,
                value,
            ];
        };
        previousOperator = "&";
        for (const domainLeaf of neutralizedDomain.toList({})) {
            if (domainLeaf.length === 3) {
                const [fieldName, operator, value] = domainLeaf;
                if (fieldName === "project_id") {
                    if (operator === "!=" && value === false) {
                        projectDomain.push(
                            previousOperator === "&"
                                ? Domain.TRUE.toList({})[0]
                                : Domain.FALSE.toList({})[0]
                        );
                    } else {
                        projectDomain.push(
                            getFieldDomain("project_id", fieldName, operator, value)
                        );
                    }
                    taskDomain.push(domainLeaf);
                    continue;
                } else if (fieldName === "task_id") {
                    taskDomain.push(getFieldDomain("task_id", fieldName, operator, value));
                    projectDomain.push(
                        previousOperator === "&"
                            ? Domain.TRUE.toList({})[0]
                            : Domain.FALSE.toList({})[0]
                    );
                    continue;
                }
            } else {
                previousOperator = domainLeaf;
            }
            taskDomain.push(domainLeaf);
            projectDomain.push(domainLeaf);
        }

        taskDomain = new Domain(taskDomain);
        projectDomain = new Domain(projectDomain);

        const domainIds = [];
        /*
         * If 'project_id' and 'task_id' is used as a section, populate an array of ids that will be used in the
         * queries in order to limit the queried data.
         */
        if (this.sectionField && fieldsToConsider.includes(this.sectionField.name)) {
            for (const sectionInfo of Object.values(this.data.sections)) {
                if (!sectionInfo.isFake) {
                    domainIds.push(sectionInfo.value[0]);
                }
            }
        }

        /*
         * Convert timesheet info returned from 'project.project' and 'project.task' queries into the right data
         * formatting.
         */
        const prepareAdditionalData = (records, fieldName) => {
            const additionalData = {};
            for (const record of records) {
                let sectionKey = false;
                let sectionValue = null;
                if (this.sectionField) {
                    sectionKey = this._generateSectionKey(record);
                    sectionValue = record[this.sectionField.name];
                }
                const rowKey = this._generateRowKey(record);
                const { domain, values } = this._generateRowDomainAndValues(record);
                if (!(sectionKey in additionalData)) {
                    additionalData[sectionKey] = {
                        value: sectionValue,
                        rows: {},
                    };
                }
                if (!(rowKey in additionalData[sectionKey].rows)) {
                    additionalData[sectionKey].rows[rowKey] = {
                        domain: domain,
                        values,
                    };
                }
            }

            return additionalData;
        };

        if (isProjectIdInDomainFields) {
            if (this.sectionField && this.sectionField.name === "project_id") {
                projectDomain = Domain.and([
                    projectDomain,
                    [["id", "in", domainIds]],
                    [["allow_timesheets", "=", true]],
                ]);
            }
            if (!this.sectionField || this.sectionField.name === "project_id") {
                additionalGroups.push(
                    this.orm
                        .webSearchRead("project.project", projectDomain.toList({}), {
                            specification: { display_name: {} },
                        })
                        .then((data) => {
                            const timesheet_data = data.records.map((r) => {
                                return { project_id: [r.id, r.display_name] };
                            });
                            return prepareAdditionalData(timesheet_data);
                        })
                );
            }
        }
        const addTaskData = (taskDomain, limit) => {
            additionalGroups.push(
                this.orm
                    .webSearchRead("project.task", taskDomain.toList({}), {
                        specification: {
                            display_name: {},
                            project_id: {
                                fields: { display_name: {} },
                            },
                        },
                        limit: limit,
                    })
                    .then((data) => {
                        const records = data.records.map(({ id, display_name, project_id }) => {
                            return {
                                task_id: [id, display_name],
                                project_id: project_id && [project_id.id, project_id.display_name],
                            };
                        });
                        return prepareAdditionalData(records);
                    })
            );
        };
        if (isProjectIdInDomainFields || isTaskIdInDomainFields) {
            if (this.sectionField?.name === "task_id") {
                taskDomain = Domain.and([
                    taskDomain,
                    [["id", "in", domainIds]],
                    [["allow_timesheets", "=", true]],
                ]);
            }
            if (!this.sectionField || isProjectOrTaskAsSectionField) {
                addTaskData(taskDomain, 15);
            }
        } else if (this.navigationInfo.periodEnd > this.model.today && !this.sectionField) {
            addTaskData(Domain.and([
                taskDomain,
                this._getFavoriteTaskDomain(),
            ]), 5);
        }

        return additionalGroups;
    }

    _getFieldValuesInSectionAndRows(field) {
        const fieldName = field.name;
        const isMany2oneField = field.type === "many2one";
        const values = new Set();
        if (this.sectionField && this.sectionField.name === fieldName) {
            for (const section of this.sectionsArray) {
                values.add(section.value && isMany2oneField ? section.value[0] : section.value);
            }
        } else if (this.rowFields.some((row) => row.name === fieldName)) {
            for (const row of this.rowsArray) {
                if (!row.isSection) {
                    const value =
                        row.valuePerFieldName[fieldName] && isMany2oneField
                            ? row.valuePerFieldName[fieldName][0]
                            : row.valuePerFieldName[fieldName];
                    values.add(value);
                }
            }
        }
        return [...values];
    }

    async _fetchWorkingHoursData(fieldName) {
        const field = this.fieldsInfo[fieldName];
        if (!field) {
            return [];
        }
        const fieldValues = this._getFieldValuesInSectionAndRows(field);
        if (!fieldValues.length) {
            return fieldValues;
        }
        const result = await this.orm.call(field.relation, "get_planned_and_worked_hours", [
            fieldValues,
        ]);
        this.data.workingHours[fieldName] = result;
    }

    async _fetchAllTimesheetM2OAvatarData() {
        const field = this.fieldsInfo.employee_id;
        if (
            !field ||
            this.navigationInfo.contains(this.model.today) ||
            this.navigationInfo.periodStart.startOf("day") > this.model.today.startOf("day")
        ) {
            return {};
        }
        const fieldValues = this._getFieldValuesInSectionAndRows(field);
        const nonEmptyValues = fieldValues.filter((v) => v !== false);
        if (!nonEmptyValues.length) {
            return {};
        }
        const result = await this.orm.call(
            field.relation,
            "get_timesheet_and_working_hours_for_employees",
            [
                nonEmptyValues,
                serializeDate(this.navigationInfo.periodStart),
                serializeDate(this.navigationInfo.periodEnd),
            ]
        );
        this.data.workingHours.employee_id = result;
    }
}

export class TimesheetGridModel extends GridModel {
    static DataPoint = TimesheetGridDataPoint;

    get workingHoursData() {
        return this.data.workingHours;
    }

    get unavailabilityDaysPerEmployeeId() {
        return this._dataPoint?.unavailabilityDaysPerEmployeeId || {};
    }
}
