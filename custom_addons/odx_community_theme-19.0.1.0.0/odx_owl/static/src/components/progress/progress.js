/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Progress extends Component {
    static template = "odx_owl.Progress";
    static props = {
        ariaLabel: { type: String, optional: true },
        ariaValueText: { type: String, optional: true },
        className: { type: String, optional: true },
        indicatorClassName: { type: String, optional: true },
        indeterminate: { type: Boolean, optional: true },
        max: { type: Number, optional: true },
        value: { type: Number, optional: true },
    };
    static defaultProps = {
        ariaValueText: "",
        className: "",
        indicatorClassName: "",
        indeterminate: false,
        max: 100,
        value: 0,
    };

    get currentValue() {
        const max = this.maximumValue;
        return Math.max(0, Math.min(Number(this.props.value) || 0, max));
    }

    get maximumValue() {
        return Math.max(1, Number(this.props.max) || 100);
    }

    get percentage() {
        return (this.currentValue / this.maximumValue) * 100;
    }

    get isIndeterminate() {
        return this.props.indeterminate || this.props.value === undefined || this.props.value === null;
    }

    get dataState() {
        if (this.isIndeterminate) {
            return "indeterminate";
        }
        if (this.currentValue >= this.maximumValue) {
            return "complete";
        }
        return "loading";
    }

    get classes() {
        return cn(
            "odx-progress",
            {
                "odx-progress--indeterminate": this.isIndeterminate,
            },
            this.props.className
        );
    }

    get indicatorClasses() {
        return cn(
            "odx-progress__indicator",
            {
                "odx-progress__indicator--indeterminate": this.isIndeterminate,
            },
            this.props.indicatorClassName
        );
    }

    get indicatorStyle() {
        if (this.isIndeterminate) {
            return "";
        }
        return `transform: translateX(-${100 - this.percentage}%);`;
    }
}
