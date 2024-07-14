/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { TimesheetDisplayTimer } from "../timesheet_display_timer/timesheet_display_timer";
import { Component, useState } from "@odoo/owl";

export class TimesheetUOMHourTimer extends Component {
    setup() {
        this.ormService = useService("orm");
        this.state = useState(this.env.timerState || {});
    }

    get displayButton() {
        return this.props.record.data.display_timer && this.props.readonly;
    }

    get iconClass() {
        const icon = this.addTimeMode ? "plus" : this.isTimerRunning ? "stop" : "play";
        const textColor = this.isTimerRunning ? "danger" : "primary";
        return `fa fa-${icon} text-${textColor}`;
    }

    get isTimerRunning() {
        return this.props.record.data.is_timer_running;
    }

    get addTimeMode() {
        return this.state.addTimeMode;
    }

    get title() {
        return this.isTimerRunning ? _t("Stop") : _t("Start");
    }

    async onClick(ev) {
        ev.preventDefault();
        const action = this.addTimeMode ? "increase" : this.isTimerRunning ? "stop" : "start";
        await this.ormService.call(
            this.props.record.resModel,
            `action_timer_${action}`,
            [[this.props.record.resId]],
            { context: this.props.context }
        );
        await this.props.record.model.load();
    }
}

TimesheetUOMHourTimer.components = { TimesheetDisplayTimer };

TimesheetUOMHourTimer.template = "timesheet_grid.TimesheetUOMHourTimer";

export const timesheetUOMHourTimer = {
    component: TimesheetUOMHourTimer,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            context: dynamicInfo.context,
        };
    },
    fieldDependencies: [
        { name: "duration_unit_amount", type: "float" },
        { name: "display_timer", type: "boolean" },
        { name: "is_timer_running", type: "boolean" },
    ],
};

registry.category("fields").add("timesheet_uom_hour_timer", timesheetUOMHourTimer);
