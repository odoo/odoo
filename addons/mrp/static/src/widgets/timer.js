import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { parseFloatTime } from "@web/views/fields/parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onWillDestroy, proxy, signal, t, useOnChange, useProps } from "@odoo/owl";

function formatMinutes(value) {
    if (value === false) {
        return "";
    }
    const isNegative = value < 0;
    if (isNegative) {
        value = Math.abs(value);
    }
    let hour = Math.floor(value / 60);
    let min = Math.floor(value % 60);
    let sec = Math.round((value % 1) * 60);
    sec = `${sec}`.padStart(1, "0");
    min = `${min}`.padStart(1, "0");
    if (hour > 0) {
        hour = `${hour}`.padStart(1, "0");
        return `${isNegative ? "-" : ""}${hour}h ${min}m ${sec}s`;
    }
    return `${isNegative ? "-" : ""}${min}m ${sec}s`;
}

export class MrpTimer extends Component {
    static template = "mrp.MrpTimer";
    props = useProps({
        value: t.number(),
        ongoing: t.boolean().optional(false),
    });

    setup() {
        this.state = proxy({
            // duration is expected to be given in minutes
            duration: this.props.value,
        });
        this.lastDateTime = Date.now();

        // Runs on mount and whenever the timer is (re)started, the cleanup
        // stopping the timers as soon as it is no longer ongoing.
        useOnChange(
            () => [this.props.ongoing],
            (ongoing) => {
                if (!ongoing) {
                    return;
                }
                this.state.duration = this.props.value;
                // Reset the reference time: the time elapsed before the timer
                // started must not be mistaken for a sleep period.
                this.lastDateTime = Date.now();
                this._runTimer();
                this._runSleepTimer();
                return () => this._stopTimers();
            }
        );
    }

    get durationFormatted() {
        return formatMinutes(this.state.duration);
    }

    _stopTimers() {
        clearTimeout(this.tickTimer);
        clearTimeout(this.sleepTimer);
    }

    _runTimer() {
        this.tickTimer = setTimeout(() => {
            this.state.duration += 1 / 60;
            this._runTimer();
        }, 1000);
    }

    //updates the time when the computer wakes from sleep mode
    _runSleepTimer() {
        this.sleepTimer = setTimeout(() => {
            const diff = Date.now() - this.lastDateTime - 10000;
            if (diff > 1000) {
                this.state.duration += diff / (1000 * 60);
            }
            this.lastDateTime = Date.now();
            this._runSleepTimer();
        }, 10000);
    }
}

class MrpTimerField extends Component {
    static template = "mrp.MrpTimerField";
    static components = { MrpTimer };
    props = useProps(standardFieldProps);

    numpadDecimalRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        useInputField({
            getValue: () => this.durationFormatted,
            ref: this.numpadDecimalRef,
            parse: (v) => parseFloatTime(v),
        });

        useRecordObserver(async (record) => {
            if (!record.model.useSampleModel && record.data.state === "progress") {
                this.duration = await this.orm.call("mrp.workorder", "get_duration", [
                    record.resId,
                ]);
            } else {
                this.duration = record.data[this.props.name];
            }
        });

        onWillDestroy(() => clearTimeout(this.timer));
    }

    get durationFormatted() {
        if (this.props.record.data[this.props.name] != this.duration && this.props.record.dirty) {
            this.duration = this.props.record.data[this.props.name];
        }
        return formatMinutes(this.duration);
    }

    get ongoing() {
        return this.props.record.data.is_user_working;
    }
}

export const mrpTimerField = {
    component: MrpTimerField,
    supportedTypes: ["float"],
};

registry.category("fields").add("mrp_timer", mrpTimerField);
registry.category("formatters").add("mrp_timer", formatMinutes);
