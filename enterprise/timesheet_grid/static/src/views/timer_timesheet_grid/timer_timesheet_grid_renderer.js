/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { deserializeDate } from "@web/core/l10n/dates";

import { TimesheetGridRenderer } from "../timesheet_grid/timesheet_grid_renderer";
import { GridTimerButtonCell } from "../../components/grid_timer_button_cell/grid_timer_button_cell";
import { GridTimesheetTimerHeader } from "../../components/grid_timesheet_timer_header/grid_timesheet_timer_header";

import { useState, useExternalListener, reactive } from "@odoo/owl";
import { session } from "@web/session";

export class TimerTimesheetGridRenderer extends TimesheetGridRenderer {
    static template = "timesheet_grid.TimerGridRenderer";
    static components = {
        ...TimesheetGridRenderer.components,
        GridTimerButtonCell,
        GridTimesheetTimerHeader,
    };

    setup() {
        super.setup();
        this.hoverTimerButtonsState = useState(
            this.getDefaultHoverTimerButtonsState(this.props.model.data)
        );
        this.timerReactive = reactive({
            cells: Object.fromEntries(
                Object.keys(this.props.model.data.rows).map((rowId) => [rowId, false])
            ),
        });
        this.timerState = useState(this.getDefaultTimerState());
        this.timesheetUOMService = useService("timesheet_uom");
        this.lastValidatedTimesheetDate = false;

        useExternalListener(window, "keyup", this.onKeyUp);
    }

    onWillUpdateProps(nextProps) {
        super.onWillUpdateProps(nextProps);
        Object.assign(
            this.hoverTimerButtonsState,
            this.getDefaultHoverTimerButtonsState(nextProps.model.data)
        );
        const newState = this.getDefaultTimerState(nextProps);
        this.timerState.timesheet = newState.timesheet;
        this.timerState.timerRunning = newState.timerRunning;
        this.timerState.otherCompany = newState.otherCompany;
        this.timerState.timerRunningRowId = newState.timerRunningRowId;
    }

    getDefaultHoverTimerButtonsState(data) {
        const res = {};
        for (const rowId in data.rows) {
            res[rowId] = false;
        }
        return res;
    }

    getDefaultTimerState(props = this.props) {
        const timerData = props.model.data.timer || {};
        return {
            timesheet: timerData.timesheet || { id: timerData.id },
            addTimeMode: false,
            startSeconds: 0,
            timerRunning: Boolean(timerData.id || timerData.other_company),
            otherCompany: Boolean(timerData.other_company),
            timerRunningRowId: timerData.row?.id || false,
        };
    }

    get columnsGap() {
        return super.columnsGap + (this.showTimerButton ? 1 : 0);
    }

    get gridTemplateColumns() {
        let gridTemplateColumns = super.gridTemplateColumns;
        if (this.showTimerButton) {
            gridTemplateColumns = `3rem ${gridTemplateColumns}`;
        }
        return gridTemplateColumns;
    }

    /**
     * Show timer feature
     *
     * @returns {boolean} returns true if the timer feature can be displayed and used.
     */
    get showTimer() {
        return this.props.model.showTimer;
    }

    /**
     * @returns {boolean} returns true if when we need to display the timer button
     *
     */
    get showTimerButton() {
        return this.props.model.showTimerButtons;
    }

    /**
     * format the overtime to display it in the total of the column
     *
     * @param {import("@web_grid/views/grid_model").DateGridColumn} column
     */
    formatDailyOvertime(column) {
        const overtime = this.getDailyOvertime(column);
        return overtime ? `${overtime > 0 ? "+" : ""}${this.formatValue(overtime)}` : "";
    }

    /**
     * Compute the overtime for a particular column
     *
     * @param {import("@web_grid/views/grid_model").DateGridColumn} column
     * @returns {number} overtime for that particular day
     */
    getDailyOvertime(column) {
        let overtime = 0;
        if (this.props.model.workingHoursData.daily.hasOwnProperty(column.value)) {
            const workingHours = this.props.model.workingHoursData.daily[column.value];
            overtime = column.grandTotal - workingHours;
        }
        return overtime;
    }

    /**
     * Format the overtime to display it in the total of the weekly summary column
     *
     * @param {number} weeklyOvertime
     * @returns {string|string}
     */
    formatWeeklyOvertime(weeklyOvertime) {
        return weeklyOvertime ? `${weeklyOvertime > 0 ? "+" : ""}${this.formatValue(weeklyOvertime)}` : "";
    }

    /**
     * Compute the overtime for the week
     *
     * @returns {number} overtime for the week
     */
    getWeeklyOvertime() {
        if (!Object.keys(this.props.model.workingHoursData.daily).length) {
            return null;
        }
        if ('full_time_required_hours' in this.props.model.workingHoursData.daily) {
            const grandTotal = this.props.model.columnsArray.reduce((total, column) => total + column.grandTotal, 0);
            return grandTotal - this.props.model.workingHoursData.daily.full_time_required_hours;
        }
        return this.props.model.columnsArray.reduce((overtime, column) => overtime + this.getDailyOvertime(column), 0);
    }

    getFooterTotalCellClasses(grandTotal) {
        const weeklyOvertime = this.getWeeklyOvertime();
        if (weeklyOvertime == null) {
            return super.getFooterTotalCellClasses(grandTotal);
        } else if (weeklyOvertime < -0.00001) {
            return "text-bg-danger";
        } else if (weeklyOvertime > -0.00001 && weeklyOvertime < 0.00001) {
            return "text-bg-success";
        } else {
            return "text-bg-warning";
        }
    }

    /**
     * @override
     * @param {KeyboardEvent} ev
     */
    onKeyDown(ev) {
        if (ev.target.closest(".modal") || ['input', 'textarea'].includes(ev.target.tagName.toLowerCase())) {
            return;
        }
        if (
            ["Shift", "Enter"].includes(ev.key) &&
            !this.timerState.timerRunning &&
            !this.isEditing
        ) {
            if (ev.key === "Enter") {
                this.onTimerStarted();
            } else {
                this.timerState.addTimeMode = true;
            }
        } else if (!ev.altKey && !ev.ctrlKey && !ev.metaKey && this.showTimerButton) {
            if (ev.key === "Escape" && this.timerState.timerRunning && !this.timerState.otherCompany) {
                this.onTimerUnlinked();
                return;
            }
            const key = ev.key.toUpperCase();
            if (
                !ev.repeat &&
                this.props.model.data.rowPerKeyBinding &&
                key in this.props.model.data.rowPerKeyBinding
            ) {
                const row = this.props.model.data.rowPerKeyBinding[key];
                if (this.timerState.addTimeMode) {
                    row.addTime();
                } else if (row.timerRunning) {
                    this.onTimerStopped(row);
                } else {
                    this.onTimerClick(row);
                }
            }
        }
        super.onKeyDown(ev);
    }
    /**
     * @param {KeyboardEvent} ev
     */
    onKeyUp(ev) {
        if (ev.key === "Shift" && !this.isEditing) {
            this.timerState.addTimeMode = false;
        }
    }

    _onMouseOver(ev) {
        const searchTimerButtonHighlighted = !this.hoveredElement;
        super._onMouseOver(ev);
        if (
            searchTimerButtonHighlighted &&
            this.hoveredElement?.dataset.row &&
            this.hoveredElement.classList.contains("o_grid_row_timer")
        ) {
            this.hoverTimerButtonsState[this.hoveredElement.dataset.row] = true;
        }
    }

    /**
     * Mouse out handler
     *
     * @param {MouseEvent} ev
     */
    _onMouseOut(ev) {
        let rowIdHighlighted;
        if (
            this.hoveredElement?.dataset.row &&
            this.hoveredElement.classList.contains("o_grid_row_timer")
        ) {
            rowIdHighlighted = this.hoveredElement.dataset.row;
        }
        super._onMouseOut(ev);
        if (
            !this.hoveredElement &&
            rowIdHighlighted &&
            this.hoverTimerButtonsState[rowIdHighlighted]
        ) {
            this.hoverTimerButtonsState[rowIdHighlighted] = false;
        }
    }

    async updateTimesheet(timesheetVals, secondsElapsed = 0) {
        let updateRowTimer = false;
        if (!this.timerState.timesheet?.id) {
            updateRowTimer = true;
        } else if (
            (timesheetVals.project_id &&
                this.timerState.timesheet.project_id !== timesheetVals.project_id) ||
            (timesheetVals.task_id && this.timerState.timesheet.task_id !== timesheetVals.task_id)
        ) {
            updateRowTimer = true;
        }
        await this.props.model.updateTimerTimesheet(timesheetVals, secondsElapsed);
        if (updateRowTimer) {
            this.timerState.timerRunningRowId = this.props.model.data.timer.row?.id || false;
        }
    }

    /**
     * Handler to start the timer
     *
     * @param {import("@timesheet_grid/views/timer_timesheet_grid/timer_timesheet_grid_model").TimerGridRow | undefined} row
     */
    async onTimerStarted(data = {}) {
        const { row, vals } = data;
        if (row) {
            await row.startTimer();
        } else {
            await this.props.model.startTimer(vals);
        }
        this.timerState.timerRunning = true;
        this.timerState.timesheet = this.props.model.data.timer;
        this.timerState.timerRunningRowId = this.props.model.data.timer.row?.id || false;
    }

    _stopTimer() {
        this.timerState.timerRunning = false;
        if (this.timerState.timerRunningRowId) {
            this.timerState.timerRunningRowId = false;
        }
    }

    /**
     * Handler to stop the timer
     *
     * @param {import("@timesheet_grid/views/timer_timesheet_grid/timer_timesheet_grid_model").TimerGridRow | undefined} row
     */
    async onTimerStopped(row = undefined) {
        if (row) {
            await row.stopTimer();
        } else {
            await this.props.model.stopTimer();
        }
        this._stopTimer();
    }

    async onTimerUnlinked() {
        if (this.timerState.timesheet.id) {
            await this.props.model.deleteTimer();
        }
        this._stopTimer();
    }

    /**
     *
     * @param {import("@web_grid/views/grid_model").GridRow} row
     */
    async onTimerClick(row) {
        if (this.timerState.addTimeMode) {
            row.addTime();
            return;
        }
        if (this.timerState.timerRunning && this.timerState.timerRunningRowId === row.id) {
            await this.onTimerStopped(row);
            return;
        }
        if (this.timerState.timerRunning) {
            if (this.timerState.timerRunningRowId) {
                await this.onTimerStopped(
                    this.props.model.data.rows[this.timerState.timerRunningRowId]
                );
            } else if (this.timerState.timesheet.project_id) {
                await this.onTimerStopped();
            }
        }
        await this.onTimerStarted({ row });
    }

    async _getLastValidatedTimesheetDate(props = this.props) {
        const res = await props.model.orm.call(
            "res.users",
            "get_last_validated_timesheet_date",
            [session.user_id],
        );
        this.lastValidatedTimesheetDate = res && deserializeDate(res);
    }

    get displayAddLine() {
        return super.displayAddLine && (!this.lastValidatedTimesheetDate || this.lastValidatedTimesheetDate.startOf("day") < this.props.model.navigationInfo.periodEnd.startOf("day"));
    }
}
