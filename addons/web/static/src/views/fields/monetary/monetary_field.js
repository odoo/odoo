/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { formatMonetary } from "../formatters";
import { parseMonetary } from "../parsers";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { standardFieldProps } from "../standard_field_props";
import { session } from "@web/session";
import { nbsp } from "@web/core/utils/strings";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

export class MonetaryField extends Component {
    setup() {
        useInputField({
            getValue: () => this.getFormattedValue(),
            refName: "numpadDecimal",
            parse: parseMonetary,
        });
        onWillUpdateProps((nextProps) => {
            this.state.value = this.getFormattedValue(nextProps);
        });
        this.state = useState({ value: this.getFormattedValue() });
        this.nbsp = nbsp;
        useNumpadDecimal();
    }

    get currencyId() {
        const currencyField =
            this.props.currencyField ||
            this.props.record.fields[this.props.name].currency_field ||
            "currency_id";
        const currency = this.props.record.data[currencyField];
        return currency && currency[0];
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

    get currencyDigits() {
        if (this.props.useFieldDigits) {
            return this.props.record.fields[this.props.name].digits;
        }
        if (!this.currency) {
            return null;
        }
        return session.currencies[this.currencyId].digits;
    }

    getFormattedValue(props = this.props) {
        if (props.inputType === "number" && !props.readonly && props.value) {
            return props.value;
        }
        return formatMonetary(props.value, {
            digits: this.currencyDigits,
            currencyId: this.currencyId,
            noSymbol: !props.readonly || props.hideSymbol,
        });
    }

    onInput(ev) {
        this.state.value = ev.target.value;
    }
}

MonetaryField.template = "web.MonetaryField";
MonetaryField.props = {
    ...standardFieldProps,
    currencyField: { type: String, optional: true },
    inputType: { type: String, optional: true },
    useFieldDigits: { type: Boolean, optional: true },
    hideSymbol: { type: Boolean, optional: true },
    placeholder: { type: String, optional: true },
};
MonetaryField.defaultProps = {
    hideSymbol: false,
    inputType: "text",
};

MonetaryField.supportedTypes = ["monetary", "float"];
MonetaryField.displayName = _lt("Monetary");

MonetaryField.extractProps = ({ attrs }) => {
    return {
        currencyField: attrs.options.currency_field,
        inputType: attrs.type,
        useFieldDigits: attrs.options.field_digits,
        hideSymbol: attrs.options.no_symbol,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("monetary", MonetaryField);
