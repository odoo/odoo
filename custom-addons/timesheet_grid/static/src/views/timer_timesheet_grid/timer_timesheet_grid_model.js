/** @odoo-module */

import { serializeDate } from "@web/core/l10n/dates";
import { GridRow } from "@web_grid/views/grid_model";
import { TimesheetGridDataPoint, TimesheetGridModel } from "../timesheet_grid/timesheet_grid_model";

export class TimerGridRow extends GridRow {
    constructor(domain, valuePerFieldName, model, section, isAdditionalRow = false) {
        super(domain, valuePerFieldName, model, section, isAdditionalRow);
        this.timerRunning = false;
    }

    async startTimer() {
        const vals = {};
        const getValue = (fieldName, value) =>
            this.model.fieldsInfo[fieldName].type === "many2one" ? value[0] : value;
        for (const [key, value] of Object.entries(this.valuePerFieldName)) {
            vals[key] = getValue(key, value);
        }
        if (!this.section.isFake) {
            vals[this.model.sectionField.name] = getValue(
                this.model.sectionField.name,
                this.section.value
            );
        }
        await this.model.startTimer(vals, this);
        this.timerRunning = true;
    }

    async stopTimer() {
        await this.model.stopTimer();
        this.timerRunning = false;
    }

    get timeData() {
        return {
            'project_id': this.valuePerFieldName?.project_id?.[0],
            'task_id': this.valuePerFieldName?.task_id?.[0],
        }
    }

    async addTime() {
        await this.model.addTime(this.timeData);
    }
}

export class TimerTimesheetGridDataPoint extends TimesheetGridDataPoint {
    constructor(model, params) {
        super(model, params);
        this.showTimerButtons =
            this.model.showTimer &&
            !this.sectionField &&
            this.rowFields.length &&
            this.rowFields.some((rowField) => rowField.name === "project_id");
    }

    get timesheetWorkingHoursPromises() {
        const promises = super.timesheetWorkingHoursPromises;
        promises.push(this.fetchDailyWorkingHours());
        return promises;
    }

    async fetchDailyWorkingHours() {
        const dailyWorkingHours = await this.orm.call("hr.employee", "get_daily_working_hours", [
            serializeDate(this.navigationInfo.periodStart),
            serializeDate(this.navigationInfo.periodEnd),
        ]);
        this.data.workingHours.daily = dailyWorkingHours;
    }

    _getAdditionalPromises() {
        const promises = super._getAdditionalPromises();
        promises.push(this._getRunningTimer());
        return promises;
    }

    async _initialiseData() {
        await super._initialiseData();
        this.data.workingHours.daily = {};
        this.data.rowPerKeyBinding = {};
        this.data.keyBindingPerRowId = {};
        this.data.stepTimer = 0;
        this.timerButtonIndex = 0;
    }

    _itemsPostProcess(item) {
        super._itemsPostProcess(item);
        if (!item.isSection && this.showTimerButtons) {
            if (this.timerButtonIndex < 26) {
                const timerButtonKey = String.fromCharCode(65 + this.timerButtonIndex++);
                this.data.rowPerKeyBinding[timerButtonKey] = item;
                this.data.keyBindingPerRowId[item.id] = timerButtonKey;
            }
        }
    }

    _updateTimer(timerData) {
        if (!this.data.timer) {
            this.data.timer = timerData;
        } else {
            for (const [key, value] of Object.entries(timerData)) {
                this.data.timer[key] = value;
            }
        }
        if (!timerData.row && this.data.timer.id) {
            // if the id linked to the timer changed then search the row associated
            this._searchRowWithTimer();
        }
    }

    _searchRowWithTimer() {
        let rowKey = `${this.sectionField ? this.data.timer[this.sectionField.name] : "false"}@|@`;
        for (const row of this.rowFields) {
            let value = this.data.timer[row.name];
            if (!value && this.fieldsInfo[row.name].type) {
                value = false;
            }
            rowKey += `${value}\\|/`;
        }
        if (rowKey in this.data.rowsKeyToIdMapping) {
            const row = this.data.rows[this.data.rowsKeyToIdMapping[rowKey]];
            row.timerRunning = true;
            if (this.data.timer.row) {
                this.data.timer.row.timerRunning = false;
            }
            this.data.timer.row = row;
            row.timerRunning = true;
        } else if (this.data.timer.row) {
            this.data.timer.row.timerRunning = false;
            delete this.data.timer.row;
        }
    }

    async _getRunningTimer() {
        if (!this.model.showTimer) {
            return;
        }
        const { step_timer: stepTimer, ...timesheetWithTimerData } = await this.orm.call(
            this.resModel,
            "get_running_timer"
        );
        if (timesheetWithTimerData.id) {
            this._updateTimer(timesheetWithTimerData);
        } else if (this.data.timer) {
            // remove running timer since there is no longer.
            if ("row" in this.data.timer) {
                this.data.timer.row.timerRunning = false;
            }
            delete this.data.timer;
        }
        this.data.stepTimer = stepTimer;
    }
}

export class TimerTimesheetGridModel extends TimesheetGridModel {
    static services = [...TimesheetGridModel.services, "timesheet_uom"];
    static Row = TimerGridRow;
    static DataPoint = TimerTimesheetGridDataPoint;

    setup(params, services) {
        super.setup(params, services);
        this.timesheetUOMService = services.timesheet_uom;
        this.fieldsInfo.project_id.required = "True";
    }

    get showTimer() {
        return this.timesheetUOMService.timesheetWidget === "float_time";
    }

    get showTimerButtons() {
        return this._dataPoint.showTimerButtons;
    }

    _setTimerData(timerData) {
        this._dataPoint._updateTimer(timerData);
    }

    async startTimer(vals = {}, row = undefined) {
        const result = await this.orm.call(this.resModel, "action_start_new_timesheet_timer", [
            vals,
        ]);
        const timesheetTimer = result || {};
        if (row) {
            timesheetTimer.row = row;
        }
        this._setTimerData(timesheetTimer || {});
    }

    /**
     * Update the timesheet in the timer header
     *
     * @param {import('@web/model/relational_model/record').Record} timesheet
     * @param {number} time the time representing in seconds to add to the timer of the timesheet
     */
    async updateTimerTimesheet(timesheetVals, time = 0.0) {
        this._setTimerData(timesheetVals);
        if (time) {
            return this.mutex.exec(async () => {
                await this.orm.call(this.resModel, "action_add_time_to_timer", [
                    timesheetVals.id,
                    time,
                ]);
            });
        }
    }

    async stopTimer() {
        const value = await this.orm.call(this.resModel, "action_timer_stop", [
            this.data.timer.id,
            true,
        ]);
        if (value) {
            const column = this.columnsArray.find((col) => col.isToday);
            if (column) {
                if (this.data.timer.row){
                    const newValue = this.data.timer.row.cells[column.id].value + value;
                    this.data.timer.row.updateCell(column, newValue);
                    this.data.timer.row.timerRunning = false;
                } else {
                    await this.fetchData(this.searchParams);
                }
            }
        }
        delete this.data.timer;
    }

    async deleteTimer() {
        await this.orm.call(this.resModel, "action_timer_unlink", [this.data.timer.id]);
        if (this.data.timer.row) {
            this.data.timer.row.timerRunning = false;
        }
        delete this.data.timer;
    }

    async addTime(data) {
        const timesheetId = this.data.timer && this.data.timer.id;
        await this.orm.call(this.resModel, "action_add_time_to_timesheet", [
            timesheetId,
            data,
        ]);
        await this.fetchData();
    }

    async fetchTimerHeaderFields(fieldNames) {
        this.timerFieldsInfo = await this.orm.call(this.resModel, "fields_get", [fieldNames]);
        return this.timerFieldsInfo;
    }
}
