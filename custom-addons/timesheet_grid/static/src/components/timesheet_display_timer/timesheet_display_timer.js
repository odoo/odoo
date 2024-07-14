/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
    Component,
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    status,
    useState,
} from "@odoo/owl";

export class TimesheetTimerFloatTimerField extends FloatTimeField {
    get formattedValue() {
        return formatFloatTime(this.value, { displaySeconds: this.props.timerRunning });
    }

    get value() {
        return this.props.value;
    }
}

TimesheetTimerFloatTimerField.template = "timesheet_grid.TimesheetTimerFloatTimeField";
TimesheetTimerFloatTimerField.props = {
    ...FloatTimeField.props,
    timerRunning: { type: Boolean },
    displayRed: { type: Boolean },
    value: true,
    name: { optional: true },
    context: { type: Object, optional: true },
};

export class TimesheetDisplayTimer extends Component {
    static template = "timesheet_grid.TimesheetDisplayTimer";

    static components = { TimesheetTimerFloatTimerField };

    static props = {
        ...standardFieldProps,
        timerRunning: { type: Boolean, optional: true },
        context: { type: Object, optional: true },
        displayRed: { type: Boolean, optional: true },
        timerService: { type: Object, optional: true },
    };

    static defaultProps = { displayRed: true };

    static fieldDependencies = {
        timer_pause: { type: "datetime" },
        timer_start: { type: "datetime" },
    };

    setup() {
        this.timerService = this.props.timerService || useService("timer");
        this.state = useState({
            timerStart: this.props.record.data.timer_start,
            timerRunning:
                Boolean(this.props.record.data.timer_start || this.props.timerRunning) &&
                !this.props.record.data.timer_pause,
            value: this.props.record.data[this.props.name],
        });
        onWillStart(this.onWillStart);
        onWillUpdateProps(this.onWillUpdateProps);
        onWillDestroy(this._stopTimeRefresh);
    }

    async onWillUpdateProps(nextProps) {
        let newValue = nextProps.record.data[nextProps.name];
        this.state.timerRunning =
            Boolean(nextProps.record.data.timer_start || nextProps.timerRunning) &&
            !nextProps.record.data.timer_pause;
        const shouldReloadTimer =
            this.props.record.data.timer_start !== nextProps.record.data.timer_start ||
            this.props.record.data.timer_pause !== nextProps.record.data.timer_pause ||
            this.props.value !== nextProps.value;
        if (this.state.timerRunning && shouldReloadTimer) {
            this._stopTimeRefresh();
            this.timerService.clearTimer();
            if (nextProps.record.data.timer_start) {
                this.state.timerStart = nextProps.record.data.timer_start;
            }
            this.timerService.setTimer(newValue, this.state.timerStart, this.serverTime);
            this.timerService.updateTimer(this.state.timerStart);
            newValue = this.timerService.floatValue;
            this._startTimeRefresh();
        }
        this.state.value = newValue;
    }

    async onWillStart() {
        if (this.state.timerRunning) {
            this.serverTime = await this.timerService.getServerTime();
            this.timerService.computeOffset(this.serverTime);
            if (!this.state.timerStart) {
                this.state.timerStart = this.timerService.getCurrentTime();
            }
            this.timerService.setTimer(this.state.value, this.state.timerStart, this.serverTime);
            this.timerService.updateTimer(this.state.timerStart);
            this.state.value = this.timerService.floatValue;
            this._startTimeRefresh();
        }
    }

    _startTimeRefresh() {
        if (!this.timeRefresh && status(this) !== "destroyed") {
            this.timeRefresh = setInterval(() => {
                this.timerService.updateTimer(this.state.timerStart);
                this.state.value = this.timerService.floatValue;
            }, 1000);
        }
    }

    _stopTimeRefresh() {
        if (this.timeRefresh) {
            clearTimeout(this.timeRefresh);
            this.timeRefresh = 0;
        }
    }

    get TimesheetTimerFloatTimerFieldProps() {
        const { timerRunning, value } = this.state;
        const props = { ...this.props };
        delete props.timerService;
        return { ...props, timerRunning, value };
    }
}
