import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "../formatters";
import { parseFloatTime } from "../parsers";
// import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

import { Component, useEffect, useRef } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";

export class FloatTimeField extends Component {
    static template = "web.FloatTimeField";
    static props = {
        ...standardFieldProps,
        inputType: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        displaySeconds: { type: Boolean, optional: true },
    };
    static defaultProps = {
        inputType: "text",
    };

    lastSetValue = "";
    unmaskedValue = "";

    setup() {
        // useInputField({
        //     getValue: () => this.formattedValue,
        //     refName: "numpadDecimal",
        //     parse: (v) => parseFloatTime(v),
        // });
        useNumpadDecimal();

        this.inputRef = useRef("numpadDecimal");

        useEffect(() => {
            if (this.inputRef.el) {
                this.inputRef.el.value = this.formattedValue;
                this.lastSetValue = this.inputRef.el.value;
            }
        });

        this.computeUnmaskedValue(
            this.props.record.data[this.props.name],
            this.props.displaySeconds
        );
        useRecordObserver((record) => {
            this.computeUnmaskedValue(record.data[this.props.name], this.props.displaySeconds);
        });
    }

    get formattedValue() {
        return formatFloatTime(this.props.record.data[this.props.name], {
            displaySeconds: this.props.displaySeconds,
        });
    }

    computeUnmaskedValue(value, displaySeconds) {
        this.unmaskedValue = formatFloatTime(value, { displaySeconds })
            .replaceAll(":", "")
            .replace(/^0+/, "");
    }

    setValue(input, value) {
        this.unmaskedValue = value;
        const paddedValue = this.unmaskedValue.padStart(4, "0");
        const hour = paddedValue.slice(0, 2);
        const minute = paddedValue.slice(2, 4);
        input.value = `${hour}:${minute}`;
    }

    /**
     * @param {InputEvent & { target: HTMLInputElement }} ev
     */
    deleteContentBackward(ev) {
        this.setValue(ev.target, this.unmaskedValue.slice(0, this.unmaskedValue.length - 1));
    }

    /**
     * @param {InputEvent & { target: HTMLInputElement }} ev
     */
    deleteWordBackward(ev) {
        this.setValue(ev.target, "");
    }

    /**
     * @param {InputEvent & { target: HTMLInputElement }} ev
     */
    insertText(ev) {
        if (!/^\d$/.test(ev.data)) {
            return;
        }

        if (this.unmaskedValue.length >= 4) {
            return;
        }

        this.setValue(ev.target, this.unmaskedValue + ev.data);
    }

    /**
     * @param {InputEvent & { target: HTMLInputElement }} ev
     */
    onBeforeInput(ev) {
        ev.preventDefault();

        switch (ev.inputType) {
            case "deleteContentBackward": {
                this.deleteContentBackward(ev);
                break;
            }
            case "deleteWordBackward": {
                this.deleteWordBackward(ev);
                break;
            }
            case "insertText": {
                this.insertText(ev);
                break;
            }
        }
    }

    async onBlur() {
        if (this.lastSetValue === this.unmaskedValue) {
            return;
        }

        let isInvalid = false;
        let value = this.inputRef.el.value;
        try {
            value = parseFloatTime(value);
        } catch {
            isInvalid = true;
            this.props.record.setInvalidField(this.props.name);
        }

        if (isInvalid) {
            return;
        }

        if (value !== this.props.record.data[this.props.name]) {
            await this.props.record.update({ [this.props.name]: value });
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", false);
        } else {
            this.inputRef.el.value = this.formattedValue;
        }
    }
}

export const floatTimeField = {
    component: FloatTimeField,
    displayName: _t("Time"),
    supportedOptions: [
        {
            label: _t("Display seconds"),
            name: "display_seconds",
            type: "boolean",
        },
        {
            label: _t("Type"),
            name: "type",
            type: "string",
            default: "text",
        },
    ],
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ attrs, options }) => ({
        displaySeconds: options.displaySeconds,
        inputType: options.type,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("float_time", floatTimeField);
