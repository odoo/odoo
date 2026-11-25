import { Component, computed, signal, t } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { formatFloat, formatInteger } from "@web/views/fields/formatters";
import { parseFloat, parseInteger } from "@web/views/fields/parsers";
import { fieldRegistry, useField } from "./field";

export class CharField extends Component {
    static template = "web.next.CharField";

    field = useField(t.or([t.string(), t.literal(false)]));
}

export class BooleanField extends Component {
    static template = "web.next.BooleanField";
    static components = { CheckBox };

    field = useField(t.boolean());
}

/**
 * A number in an input. What the user types is parsed when the input changes:
 * a value that does not parse is not written, and the input is marked invalid
 * until it does.
 */
class NumericField extends Component {
    static template = "web.next.NumericField";

    field = useField(t.number());
    invalid = signal(false);

    /** @type {(value: number | false) => string} */
    format = formatInteger;
    /** @type {(value: string) => number} */
    parse = parseInteger;

    formattedValue = computed(() => this.format(this.field.value()));

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
        this.field.value.set(value);
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
