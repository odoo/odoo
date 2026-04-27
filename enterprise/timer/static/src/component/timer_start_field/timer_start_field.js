/** @odoo-module */

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useTimer } from "../../hooks/use_timer";

export class TimerStartField extends Component {
    static props = {
        ...standardFieldProps,
    };
    static template = "timer.TimerStartField";

    setup() {
        super.setup(...arguments);
        this.timerReactive = useState(useTimer());

        useRecordObserver(this.onRecordChange.bind(this));
        onWillUnmount(() => {
            clearInterval(this.timer);
        });
    }

    onRecordChange(record) {
        clearInterval(this.timer);
        const timerPause = record.data.timer_pause;
        if (timerPause && !record.data.timer_pause) {
            this.timerReactive.clearTimer();
        }
        this.startTimer(record.data[this.props.name], timerPause);
    }

    startTimer(timerStart, timerPause) {
        if (timerStart) {
            let currentTime;
            if (timerPause) {
                currentTime = timerPause;
            } else {
                currentTime = this.timerReactive.getCurrentTime();
            }
            this.timerReactive.setTimer(0, timerStart, currentTime);
            this.timerReactive.formatTime();
            clearInterval(this.timer);
            this.timer = setInterval(() => {
                if (timerPause) {
                    clearInterval(this.timer);
                } else {
                    this.timerReactive.updateTimer(timerStart);
                    this.timerReactive.formatTime();
                }
            }, 1000);
        } else if (!timerPause) {
            clearInterval(this.timer);
            this.timerReactive.clearTimer();
        }
    }
}

export const timerStartField = {
    component: TimerStartField,
    fieldDependencies: [ { name: "timer_pause", type: "datetime" } ],
};

registry.category("fields").add("timer_start_field", timerStartField);
