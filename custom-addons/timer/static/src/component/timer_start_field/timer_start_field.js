/** @odoo-module */

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class TimerStartField extends Component {
    setup() {
        super.setup(...arguments);
        this.timerService = useService("timer");
        this.state = useState({ timer: undefined, time: "", serverOffset: 0 });

        onWillStart(this.onWillStart);
        useRecordObserver(this.onRecordChange.bind(this));
        onWillUnmount(() => {
            clearInterval(this.state.timer);
        });
    }

    async onWillStart() {
        const serverTime = await this.timerService.getServerTime();
        this.timerService.computeOffset(serverTime);
        this.state.serverOffset = this.timerService.offset;
    }

    onRecordChange(record) {
        clearInterval(this.state.timer);
        this.state.timer = undefined;
        const timerPause = record.data.timer_pause;
        if (timerPause && !record.data.timer_pause) {
            this.timerService.clearTimer();
        }
        this.startTimer(record.data[this.props.name], timerPause);
    }

    startTimer(timerStart, timerPause) {
        if (timerStart) {
            let currentTime;
            if (timerPause) {
                currentTime = timerPause;
                this.timerService.computeOffset(currentTime);
            } else {
                this.timerService.offset = this.state.serverOffset;
                currentTime = this.timerService.getCurrentTime();
            }
            this.timerService.setTimer(0, timerStart, currentTime);
            this.state.time = this.timerService.timerFormatted;
            clearInterval(this.state.timer);
            this.state.timer = setInterval(() => {
                if (timerPause) {
                    clearInterval(this.state.timer);
                } else {
                    this.timerService.updateTimer(timerStart);
                    this.state.time = this.timerService.timerFormatted;
                }
            }, 1000);
        } else if (!timerPause) {
            clearInterval(this.state.timer);
            this.state.time = "";
            this.timerService.clearTimer();
        }
    }
}

TimerStartField.props = {
    ...standardFieldProps,
};
TimerStartField.template = "timer.TimerStartField";

export const timerStartField = {
    component: TimerStartField,
    fieldDependencies: [ { name: "timer_pause", type: "datetime" } ],
};

registry.category("fields").add("timer_start_field", timerStartField);
