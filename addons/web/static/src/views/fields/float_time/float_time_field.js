import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatDuration } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { parseDuration, parseFloatTime } from "../parsers";

import { Component, useState } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { exprToBoolean } from "@web/core/utils/strings";

export class FloatTimeField extends Component {
    static template = "web.FloatTimeField";
    static props = {
        ...standardFieldProps,
        showSeconds: { type: Boolean, optional: true },
        numeric: { type: Boolean, optional: true },
        unit: { type: ["hours", "minutes", "seconds"], optional: true },
    };
    static defaultProps = {
        numeric: false,
        unit: "hours",
    };

    setup() {
        this.inputFloatTimeRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseFloatTime(v, this.props.unit),
        });

        this.state = useState({
            formattedResult: "",
        });
        this.resultPopover = usePopover(DurationPopover, {
            position: "bottom",
        });
        useNumpadDecimal();
    }

    onValueChange(ev) {
        const currentInput = ev.target.value;
        this.state.formattedResult = formatDuration(parseDuration(currentInput, this.props.unit), {
            showSeconds: this.props.showSeconds,
            numeric: this.props.numeric,
            unit: this.props.unit,
        });
        if (currentInput === this.state.formattedResult && this.resultPopover.isOpen) {
            this.resultPopover.close();
        } else if (currentInput !== this.state.formattedResult && !this.resultPopover.isOpen) {
            this.resultPopover.open(this.inputFloatTimeRef.el, {
                state: this.state,
            });
        }
    }

    openPopover() {
        const duration = parseDuration(this.inputFloatTimeRef.el.value, this.props.unit);
        this.state.formattedResult = formatDuration(duration, {
            showSeconds: this.props.showSeconds,
            numeric: this.props.numeric,
            unit: this.props.unit,
        });
        this.resultPopover.open(this.inputFloatTimeRef.el, {
            state: this.state,
        });
    }

    closePopover() {
        this.resultPopover.close();
    }

    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        return formatDuration(
            {
                [this.props.unit]: value,
            },
            {
                showSeconds: this.props.showSeconds,
                numeric: this.props.numeric,
                unit: this.props.unit,
            },
        );
    }
}

class DurationPopover extends Component {
    static template = "web.DurationPopover";
    static props = {
        state: { type: Object, optional: true },
        close: { type: Function, optional: true },
    };
}

export const floatTimeField = {
    component: FloatTimeField,
    displayName: _t("Time"),
    supportedOptions: [
        {
            label: _t("Show seconds"),
            name: "show_seconds",
            type: "boolean",
        },
        {
            label: _t("Type"),
            name: "type",
            type: "string",
            default: "text",
        },
        {
            label: _t("Numeric"),
            name: "numeric",
            type: "boolean",
        },
        {
            label: _t("Unit"),
            name: "unit",
            type: "selection",
            default: "hours",
            choices: [
                { label: _t("Hours"), value: "hours" },
                { label: _t("Minutes"), value: "minutes" },
                { label: _t("Seconds"), value: "seconds" },
            ],
        },
    ],
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ options }) => ({
        showSeconds: exprToBoolean(options.show_seconds),
        numeric: exprToBoolean(options.numeric),
        unit: options.unit,
    }),
};

registry.category("fields").add("float_time", floatTimeField);
