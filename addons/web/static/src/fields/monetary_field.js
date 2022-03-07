/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";
import { session } from "@web/session";

const { Component } = owl;

export class MonetaryField extends Component {
    onChange(ev) {
        let isValid = true;
        let value = ev.target.value;
        try {
            value = this.props.parseValue(value, { currencyId: this.currencyId });
        } catch (e) {
            isValid = false;
            this.props.record.setInvalidField(this.props.name);
            if (this.__owl__.app.dev) console.warn(e.message);
        }
        if (isValid) {
            this.props.update(value);
        }
    }

    get currencyId() {
        if (this.props.record.activeFields[this.props.name].options.currency_field) {
            return this.props.record.data[
                this.props.record.activeFields[this.props.name].options.currency_field
            ][0];
        }
        return this.props.record.data.currency_id && this.props.record.data.currency_id[0];
    }

    get currency() {
        if (!isNaN(this.currencyId) && this.currencyId in session.currencies) {
            return session.currencies[this.currencyId];
        }
        return null;
    }

    get currencySymbol() {
        return this.currency ? this.currency.symbol : "";
    }

    get currencyPosition() {
        return this.currency && this.currency.position;
    }

    get formattedValue() {
        return this.props.formatValue(this.props.value, {
            digits: this.currencyDigits,
            field: this.props.record.fields[this.props.name],
            currencyId: this.currencyId,
        });
    }

    get currencyDigits() {
        if (this.props.digits) return this.props.digits;
        if (!this.currency) return null;
        return session.currencies[this.currencyId].digits;
    }

    get formattedInputValue() {
        if (this.props.inputType === "number") {
            return this.props.value;
        }
        return this.props.formatValue(this.props.value, {
            digits: this.currencyDigits,
            field: this.props.record.fields[this.props.name],
            noSymbol: true,
        });
    }
}

MonetaryField.template = "web.MonetaryField";
MonetaryField.supportedTypes = ["monetary", "float"];
MonetaryField.displayName = _lt("Monetary");

MonetaryField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    digits: { type: Array, optional: true },
};
MonetaryField.defaultProps = {
    inputType: "text",
};

MonetaryField.extractProps = function (fieldName, record, attrs) {
    return {
        inputType: attrs.type,
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        digits: attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits,
    };
};

registry.category("fields").add("monetary", MonetaryField);
