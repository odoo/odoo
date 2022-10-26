/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { formatMonetary } from "../formatters";
import { parseMonetary } from "../parsers";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { standardFieldProps } from "../standard_field_props";
import { session } from "@web/session";

const { Component } = owl;

export class MonetaryField extends Component {
    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseMonetary(v, { currencyId: this.currencyId }),
        });
        useNumpadDecimal();
    }

    get currencyId() {
        return this.props.currencyField
            ? this.props.record.data[this.props.currencyField][0]
            : (this.props.record.data.currency_id && this.props.record.data.currency_id[0]) ||
                  undefined;
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
        if (this.props.digits) {
            return this.props.digits;
        }
        if (!this.currency) {
            return null;
        }
        return session.currencies[this.currencyId].digits;
    }

    get formattedValue() {
        if (this.props.inputType === "number" && !this.props.readonly && this.props.value) {
            return this.props.value;
        }
        return formatMonetary(this.props.value, {
            digits: this.currencyDigits,
            currencyId: this.currencyId,
            noSymbol: !this.props.readonly || this.props.hideSymbol,
        });
    }
}

MonetaryField.template = "web.MonetaryField";
MonetaryField.props = {
    ...standardFieldProps,
    currencyField: { type: String, optional: true },
    inputType: { type: String, optional: true },
    digits: { type: Array, optional: true },
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
        digits: [16, 2], // FIXME WOWL
        hideSymbol: attrs.options.no_symbol,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("monetary", MonetaryField);
