import { Component, markup, t, useProps } from "@odoo/owl";
import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";
import {
    formatDate,
    formatDateTime,
    formatFloat,
    formatInteger,
    formatSelection,
} from "@web/views/fields/formatters";

const NUMBER_TYPES = ["integer", "float", "monetary"];
/** types that have an input, the others are always displayed read only */
const EDITABLE_TYPES = ["char", "text", "boolean", "selection", "date", ...NUMBER_TYPES];

/**
 * One field of the record: an input to edit it, or its formatted value.
 *
 * The field is read from the record as a signal, `record[name]()`, so this
 * component subscribes to that field only: typing in another field does not
 * render it again. Edits are written back with `record[name].set(value)`.
 */
export class FormSignalField extends Component {
    static template = "web.FormSignalField";

    props = useProps({
        record: t.object(),
        name: t.string(),
        /** the field description, from `fields_get` */
        field: t.object(),
        readonly: t.boolean().optional(false),
    });

    type() {
        return this.props.field.type;
    }

    value() {
        return this.props.record[this.props.name]();
    }

    isEditable() {
        return !this.props.readonly && EDITABLE_TYPES.includes(this.type());
    }

    /** value for the input, see `onInput` and `onChange` for the other way around */
    inputValue() {
        const value = this.value();
        return NUMBER_TYPES.includes(this.type()) ? value ?? 0 : value || "";
    }

    /** value displayed in read only mode */
    displayValue() {
        const { field } = this.props;
        const value = this.value();
        if (value === undefined || value === null || value === false) {
            return "";
        }
        switch (this.type()) {
            case "integer":
                return formatInteger(value);
            case "float":
            case "monetary":
                return formatFloat(value, { digits: field.digits });
            case "date":
                return formatDate(deserializeDate(value));
            case "datetime":
                return formatDateTime(deserializeDateTime(value));
            case "selection":
                return formatSelection(value, { selection: field.selection });
            case "many2one":
                return value.display_name();
            case "one2many":
            case "many2many":
                return value.map((record) => record.display_name()).join(", ");
            case "html":
                return markup(value);
            default:
                return String(value);
        }
    }

    /**
     * Writes as the user types: the value only changes when the input holds
     * a valid one, e.g. not while a number is being typed ("-", "1e").
     *
     * @param {InputEvent & { target: HTMLInputElement }} ev
     */
    onInput(ev) {
        if (NUMBER_TYPES.includes(this.type())) {
            const value = ev.target.valueAsNumber;
            if (!Number.isNaN(value)) {
                this.props.record[this.props.name].set(value);
            }
        } else {
            this.props.record[this.props.name].set(ev.target.value || false);
        }
    }

    /**
     * @param {Event & { target: HTMLInputElement }} ev
     */
    onChange(ev) {
        let value;
        if (this.type() === "boolean") {
            value = ev.target.checked;
        } else if (NUMBER_TYPES.includes(this.type())) {
            // left empty or invalid
            value = Number.isNaN(ev.target.valueAsNumber) ? 0 : ev.target.valueAsNumber;
        } else {
            value = ev.target.value || false;
        }
        this.props.record[this.props.name].set(value);
    }
}
