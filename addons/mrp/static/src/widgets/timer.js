/** @odoo-module **/

import { registry } from "@web/core/registry";
import { parseFloatTime } from "@web/views/fields/parsers";
import { useInputField } from "@web/views/fields/input_field_hook";

const { Component, useState, onWillUpdateProps, onWillStart, onWillDestroy } = owl;

export class MrpTimer extends Component {
    setup() {
        this.state = useState({
            // duration is expected to be given in minutes
            duration:
                this.props.value !== undefined ? this.props.value : this.props.record.data.duration,
        });
        useInputField({
            getValue: () => this.durationFormatted,
            refName: "numpadDecimal",
            parse: (v) => parseFloatTime(v),
        });

        this.ongoing =
            this.props.ongoing !== undefined
                ? this.props.ongoing
                : this.props.record.data.is_user_working;

        onWillStart(() => this._runTimer());
        onWillUpdateProps((nextProps) => {
            this.state.duration = nextProps.value;
            const newOngoing =
                "ongoing" in nextProps
                    ? nextProps.ongoing
                    : "record" in nextProps && nextProps.record.data.is_user_working;
            const rerun = !this.ongoing && newOngoing;
            this.ongoing = newOngoing;
            if (rerun) {
                this._runTimer();
            }
        });
        onWillDestroy(() => clearTimeout(this.timer));
    }

    get durationFormatted() {
        return this._formatMinutes();
    }

    _runTimer() {
        if (this.ongoing) {
            this.timer = setTimeout(() => {
                this.state.duration += 1 / 60;
                this._runTimer();
            }, 1000);
        }
    }

    _formatMinutes() {
        let value = this.state.duration;
        if (value === false) {
            return "";
        }
        const isNegative = value < 0;
        if (isNegative) {
            value = Math.abs(value);
        }
        let min = Math.floor(value);
        // Although looking quite overkill, the following line ensures that we do
        // not have float issues while still considering that 59s is 00:00.
        let sec = Math.floor(Math.round((value % 1) * 60));
        sec = `${sec}`.padStart(2, "0");
        min = `${min}`.padStart(2, "0");
        return `${isNegative ? "-" : ""}${min}:${sec}`;
    }
}

MrpTimer.supportedTypes = ["float"];
MrpTimer.template = "mrp.MrpTimer";

registry.category("fields").add("mrp_timer", MrpTimer);
