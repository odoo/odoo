import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { DurationParseError, InvalidNumberError, parseFloatTime } from "../parsers";
import { Operation } from "@web/model/relational_model/operation";

import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";

export const floatTimeFieldProps = {
    ...standardFieldProps,
    showSeconds: t.boolean().optional(),
    numeric: t.boolean().optional(false),
    unit: t.selection(["hours", "minutes", "seconds"]).optional("hours"),
};

export class FloatTimeField extends Component {
    static template = "web.FloatTimeField";
    props = useProps(floatTimeFieldProps);
    numpadDecimalRef = signal.ref();

    setup() {
        this.inputFloatTimeRef = useInputField({
            getValue: () => this.formattedValue,
            ref: this.numpadDecimalRef,
            parse: (v) => this.parseValue(v),
        });

        this.state = proxy({
            formattedResult: "",
        });
        this.resultPopover = usePopover(DurationPopover, {
            position: "bottom",
        });
        useNumpadDecimal(this.numpadDecimalRef);
    }

    get formatOptions() {
        return {
            showSeconds: this.props.showSeconds,
            numeric: this.props.numeric,
            unit: this.props.unit,
        };
    }

    onValueChange(ev) {
        const currentInput = ev.target.value;
        const parsedValue = this.parseOrClosePopover(currentInput);

        if (parsedValue || parsedValue === 0) {
            this.state.formattedResult = formatFloatTime(parsedValue, this.formatOptions);
            if (currentInput === this.state.formattedResult && this.resultPopover.isOpen) {
                this.resultPopover.close();
            } else if (currentInput !== this.state.formattedResult && !this.resultPopover.isOpen) {
                this.resultPopover.open(this.inputFloatTimeRef(), {
                    state: this.state,
                });
            }
        } else {
            this.resultPopover.close();
        }
    }

    openPopover() {
        const duration = this.parseOrClosePopover(this.inputFloatTimeRef().value);
        if (duration || duration === 0) {
            this.state.formattedResult = formatFloatTime(duration, this.formatOptions);
            this.resultPopover.open(this.inputFloatTimeRef(), {
                state: this.state,
            });
        }
    }

    closePopover() {
        this.resultPopover.close();
    }

    parseOrClosePopover(value) {
        try {
            const parsed = this.parseValue(value);
            return parsed instanceof Operation ? parsed.compute(this.value) : parsed;
        } catch (error) {
            if (
                [EvalError, InvalidNumberError, DurationParseError].every(
                    (e) => !(error instanceof e)
                )
            ) {
                throw error;
            }
            this.closePopover();
        }
    }

    parseValue(value) {
        return parseFloatTime(value, this.props.unit);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get formattedValue() {
        return formatFloatTime(this.value, this.formatOptions);
    }
}

class DurationPopover extends Component {
    static template = "web.DurationPopover";
    props = useProps({
        state: t.object().optional(),
        close: t.function().optional(),
    });
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
        showSeconds: Boolean(options.show_seconds),
        numeric: Boolean(options.numeric),
        unit: options.unit,
    }),
};

registry.category("fields").add("float_time", floatTimeField);
