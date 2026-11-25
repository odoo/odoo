import { Component, signal, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { formatFloat, formatInteger } from "@web/views/fields/formatters";
import { parseFloat, parseInteger } from "@web/views/fields/parsers";
import { fieldProps, fieldRegistry } from "./field";

export class CharField extends Component {
    static template = "web.next.CharField";

    props = useProps(fieldProps);

    get value() {
        return this.props.record[this.props.name]() || "";
    }

    /**
     * @param {Event & { target: HTMLInputElement }} ev
     */
    onChange(ev) {
        this.props.record[this.props.name].set(ev.target.value);
    }
}

export class BooleanField extends Component {
    static template = "web.next.BooleanField";
    static components = { CheckBox };

    props = useProps(fieldProps);

    get value() {
        return Boolean(this.props.record[this.props.name]());
    }

    /**
     * @param {boolean} value
     */
    onChange(value) {
        this.props.record[this.props.name].set(value);
    }
}

/**
 * A number in an input. What the user types is parsed when the input changes:
 * a value that does not parse is not written, and the input is marked invalid
 * until it does.
 */
class NumericField extends Component {
    static template = "web.next.NumericField";

    props = useProps(fieldProps);
    invalid = signal(false);

    /** @type {(value: number | false) => string} */
    format = formatInteger;
    /** @type {(value: string) => number} */
    parse = parseInteger;

    get formattedValue() {
        return this.format(this.props.record[this.props.name]());
    }

    /**
     * @param {Event & { target: HTMLInputElement }} ev
     */
    onChange(ev) {
        let value;
        try {
            value = this.parse(ev.target.value);
        } catch {
            this.invalid.set(true);
            return;
        }
        this.invalid.set(false);
        this.props.record[this.props.name].set(value);
    }
}

export class IntegerField extends NumericField {}

export class FloatField extends NumericField {
    format = formatFloat;
    parse = parseFloat;
}

fieldRegistry
    .add("char", CharField)
    .add("boolean", BooleanField)
    .add("integer", IntegerField)
    .add("float", FloatField);
