import { Component, useEffect, useState } from "@odoo/owl";

export class ImportDataProgress extends Component {
    static template = "ImportDataProgress";
    static props = {
        importProgress: { type: Object },
        stopImport: { type: Function },
        totalSteps: { type: Number },
    };

    setup() {
        this.timer = undefined;
        this.timeStart = Date.now();
        this.state = useState({
            isInterrupted: false,
            timeLeft: null,
        });

        useEffect(
            () => {
                this.updateTimer();
                return () => {
                    clearInterval(this.timer);
                };
            },
            () => []
        );
    }

    get minutesLeft() {
        return this.state.timeLeft.toFixed(2);
    }

    get secondsLeft() {
        return Math.round(this.state.timeLeft * 60);
    }

    interrupt() {
        this.state.isInterrupted = true;
        this.props.stopImport();
    }

    updateTimer() {
        if (this.timer) {
            clearInterval(this.timer);
        }
        this.state.timeLeft =
            ((Date.now() - this.timeStart) *
                ((100 - this.props.importProgress.value) / this.props.importProgress.value)) /
            60000;
        this.timer = setInterval(() => this.updateTimer(), 1000);
    }
}
