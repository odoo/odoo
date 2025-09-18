// @ts-check

/** @module @web/views/kanban/column_progress - Progress bar with colored segments for kanban column group aggregates */

import { Component } from "@odoo/owl";

import { AnimatedNumber } from "./animated_number";

/** Renders a progress bar with colored segments for a kanban column group, showing aggregate totals. */
export class ColumnProgress extends Component {
    static components = {
        AnimatedNumber,
    };
    static template = "web.ColumnProgress";
    static props = {
        aggregate: { type: Object },
        group: { type: Object },
        onBarClicked: { type: Function, optional: true },
        progressBar: { type: Object },
    };
    static defaultProps = {
        onBarClicked: () => {},
    };

    /**
     * @param {Object} bar - progress bar segment that was clicked
     * @returns {Promise<void>}
     */
    async onBarClick(bar) {
        await this.props.onBarClicked(bar);
    }
}
