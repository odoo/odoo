import { Component, onMounted, onWillUnmount, signal, t, useProps } from "@odoo/owl";

export class ImportDataProgress extends Component {
    static template = "ImportDataProgress";

    props = useProps({
        importProgress: t.object(),
        stopImport: t.function(),
        totalSteps: t.number(),
    });

    isInterrupted = signal(false);
    timeLeft = signal(null);

    setup() {
        this.timeStart = Date.now();
        onMounted(() => this.updateTimer());
        onWillUnmount(() => clearInterval(this.timer));
    }

    get minutesLeft() {
        return this.timeLeft().toFixed(2);
    }

    get secondsLeft() {
        return Math.round(this.timeLeft() * 60);
    }

    interrupt() {
        this.isInterrupted.set(true);
        this.props.stopImport();
    }

    updateTimer() {
        if (this.timer) {
            clearInterval(this.timer);
        }
        this.timeLeft.set(
            ((Date.now() - this.timeStart) *
                ((100 - this.props.importProgress.value) / this.props.importProgress.value)) /
                60000
        );
        this.timer = setInterval(() => this.updateTimer(), 1000);
    }
}
