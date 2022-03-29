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
            value = this.props.parse(value, { currencyId: this.props.currencyId });
        } catch {
            isValid = false;
            this.props.setAsInvalid(this.props.name);
        }
        if (isValid) {
            this.props.update(value);
        }
    }

    get currency() {
        if (!isNaN(this.props.currencyId) && this.props.currencyId in session.currencies) {
            return session.currencies[this.props.currencyId];
        }
        return null;
    }

    get currencySymbol() {
        return this.currency ? this.currency.symbol : "";
    }

    get currencyPosition() {
        return this.currency && this.currency.position;
    }

    get currencyDigits() {
        if (this.props.digits) return this.props.digits;
        if (!this.currency) return null;
        return session.currencies[this.props.currencyId].digits;
    }

    get formattedValue() {
        if (this.props.inputType === "number" && !this.props.readonly && this.props.value) {
            return this.props.value;
        }
        return this.props.format(this.props.value, {
            digits: this.currencyDigits,
            currencyId: this.props.currencyId,
            noSymbol: !this.props.readonly,
        });
    }
}

MonetaryField.template = "web.MonetaryField";
MonetaryField.supportedTypes = ["monetary", "float"];
MonetaryField.displayName = _lt("Monetary");

MonetaryField.props = {
    ...standardFieldProps,
    currencyId: { type: Number, optional: true },
    inputType: { type: String, optional: true },
    digits: { type: Array, optional: true },
    setAsInvalid: { type: Function, optional: true },
};
MonetaryField.defaultProps = {
    inputType: "text",
    setAsInvalid: () => {},
};

MonetaryField.extractProps = function (fieldName, record, attrs) {
    return {
        currencyId: attrs.options.currency_field
            ? record.data[attrs.options.currency_field][0]
            : (record.data.currency_id && record.data.currency_id[0]) || undefined,
        inputType: attrs.type,
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        digits: attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits,
        setAsInvalid: record.setInvallidField,
    };
};

registry.category("fields").add("monetary", MonetaryField);
