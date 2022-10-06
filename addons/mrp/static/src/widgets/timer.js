/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatFloatTime } from "@web/views/fields/formatters";

const { Component, useState, onWillUpdateProps, onWillStart, onWillDestroy } = owl;

export class MrpTimer extends Component {
    setup() {
        super.setup();
        this.state = useState({
            duration:
                this.props.duration !== undefined
                    ? this.props.duration
                    : this.props.record.data.duration,
        });

        const newLocal = this;
        this.ongoing =
            this.props.ongoing !== undefined
                ? newLocal.props.ongoing
                : this.props.record.data.is_user_working;

        onWillStart(() => this._runTimer());
        onWillUpdateProps((nextProps) => {
            this.ongoing = nextProps.ongoing;
            this._runTimer();
        });
        onWillDestroy(() => clearTimeout(this.timer));
    }

    get duration() {
        // formatFloatTime except 1,5 =  1h30min but in mrp case 1,5 = 1min30
        return formatFloatTime(this.state.duration / 60, { displaySeconds: true });
    }

    _runTimer() {
        if (this.ongoing) {
            this.timer = setTimeout(() => {
                this.state.duration += 1 / 60;
                this._runTimer();
            }, 1000);
        }
    }
}

MrpTimer.supportedTypes = ["float"];
MrpTimer.template = "mrp.MrpTimer";

registry.category("fields").add("mrp_timer", MrpTimer);
