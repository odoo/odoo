import { Component } from "@odoo/owl";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";

export class GanttRowProgressBar extends Component {
    static props = {
        reactive: {
            type: Object,
            shape: {
                hoveredRowId: [String, { value: null }],
            },
        },
        rowId: String,
        progressBar: {
            type: Object,
            shape: {
                max_value: Number,
                max_value_formatted: String,
                ratio: Number,
                value_formatted: String,
                warning: { type: String, optional: true },
                "*": true,
            },
        },
    };
    static template = "web_gantt.GanttRowProgressBar";

    get show() {
        const { reactive, rowId } = this.props;
        return reactive.hoveredRowId === rowId || isMobileOS() || hasTouch();
    }

    get status() {
        const { ratio } = this.props.progressBar;
        return ratio > 100 ? "danger" : ratio > 0 ? "success" : null;
    }
}
