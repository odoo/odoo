/** @odoo-module */

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

export class GridTimerButtonCell extends Component {
    static template = "timesheet_grid.GridTimerButtonCell";
    static props = {
        hotKey: { type: String, optional: true },
        row: Object,
        addTimeMode: Boolean,
        hovered: { type: Boolean, optional: true },
        timerRunning: { type: Boolean, optional: true },
        onTimerClick: Function,
    };

    setup() {
        this.state = useState({
            timerRunning: this.props.timerRunning || this.props.row.timerRunning,
        });
        onWillUpdateProps(this.onWillUpdateProps);
    }

    onWillUpdateProps(nextProps) {
        this.state.timerRunning = nextProps.timerRunning || nextProps.row.timerRunning;
    }
}
