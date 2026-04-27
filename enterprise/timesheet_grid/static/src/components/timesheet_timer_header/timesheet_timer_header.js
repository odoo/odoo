/** @odoo-module **/

import { Field, getPropertyFieldInfo } from "@web/views/fields/field";
import { TimesheetDisplayTimer } from "../timesheet_display_timer/timesheet_display_timer";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, onWillStart, useRef, useExternalListener } from "@odoo/owl";

export class TimesheetTimerHeader extends Component {
    static template = "timesheet_grid.TimesheetTimerHeader";
    static components = {
        TimesheetDisplayTimer,
        Field,
    };
    static props = {
        timesheet: { type: Object, optional: true },
        stepTimer: Number,
        timerRunning: Boolean,
        addTimeMode: Boolean,
        fields: { type: Object, optional: true },
        otherCompany: { type: Boolean, optional: true },
        timerReactive: { type: Object, optional: true },
        onTimerStarted: Function,
        onTimerStopped: Function,
        onTimerUnlinked: Function,
        onClick: { type: Function, optional: true },
        className: { type: String, optional: true },
    };
    static defaultProps = {
        onClick() {},
    };

    setup() {
        this.orm = useService("orm");
        this.startButton = useRef("startButton");
        this.stopButton = useRef("stopButton");
        onWillStart(async () => await this.onWillStart());
        useAutofocus({ refName: "startButton" });
        useAutofocus({ refName: "stopButton" });
        useExternalListener(document.body, "click", (ev) => {
            if (
                ev.target.closest(".modal, .popover") ||
                ["input", "textarea"].includes(ev.target.tagName.toLowerCase())
            ) {
                return;
            }
            this.startButton.el ? this.startButton.el.focus() : this.stopButton.el.focus();
        });
    }

    async onWillStart() {
        this.isProjectManager = await user.hasGroup('project.group_project_manager');
    }

    getIsProjectManager() {
        return this.isProjectManager;
    }

    // deprecated
    onWillUpdateProps(nextProps) {
        if (nextProps.timesheet && nextProps.timesheet.data.name === "/") {
            this._clearTimesheetName(nextProps.timesheet);
        }
    }

    //----------------------------------------------------------------------
    // Getters
    //----------------------------------------------------------------------

    get _addTimeMode() {
        return this.props.addTimeMode;
    }

    get _timerIsRunning() {
        return this.props.timerRunning;
    }

    get otherCompany() {
        return this.props.otherCompany;
    }

    get isMobile() {
        return this.env.isSmall;
    }

    get viewType() {
        return this.env.config.viewType;
    }

    getFieldType(fieldName) {
        if (fieldName === "task_id") {
            return "task_with_hours";
        }
        return this.props.fields[fieldName].type;
    }

    get fieldsInfo() {
        return {
            task_id: {
                ...getPropertyFieldInfo({ name: "task_id", type: this.getFieldType("task_id") }),
                viewType: this.viewType,
                context: this.props.fields.task_id.context,
            },
        };
    }

    //--------------------------------------------------------------------------
    // Business Methods
    //--------------------------------------------------------------------------
    // deprecated
    _clearTimesheetName(timesheet = null) {
            (timesheet || this.props.timesheet).update({ name: "" }, { silent: true });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    async _onClickStartTimer(ev) {
        await this.props.onTimerStarted();
    }

    async _onClickStopTimer(ev) {
        if (await this.props.timesheet?.save()) {
            await this.props.onTimerStopped();
        }
    }

    async _onClickUnlinkTimer(ev) {
        await this.props.onTimerUnlinked();
    }

    _onKeyDown(ev) {
        if (ev.key === 'Enter') {
            this._onClickStopTimer();
        }
    }
}
