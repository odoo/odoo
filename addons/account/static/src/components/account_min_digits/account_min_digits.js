import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";
import {floatField, FloatField } from "@web/views/fields/float/float_field";

class AccountMinDigits extends FloatField {
    static props = {
        ...FloatField.props,
        minDecimalPrecision: [Number, String],
    }

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async() => {
            if (typeof this.props.minDecimalPrecision === 'string') {
                this.minDigits = await this.orm.call(
                    "decimal.precision",
                    "precision_get",
                    [this.props.minDecimalPrecision],
                )
            }
            else {
                this.minDigits = this.props.minDecimalPrecision;
            }
        });
    }

    /*
     * @override
     * We don't want to display all amounts with 12 digits behind so we remove the trailing 0
     * as much as possible.
     */
    get formattedValue() {
        const [, decPart = ""] = this.value.toString().split(".");
        let digits;
        if (decPart.length < this.minDigits) {
            digits = this.minDigits;
        } else {
            digits = Math.min(12, decPart.length);
        }
        const options = {
            digits: [16, digits],
            field: this.props.record.fields[this.props.name],
        };
        return formatFloat(this.value, options);
    }
}

const accountMinDigits = {
    ...floatField,
    component: AccountMinDigits,
    supportedOptions : [
        ...floatField.supportedOptions,
        {
            label: _t("Minimum Precision"),
            name: 'min_decimal_precision',
            type: ['number', 'string'],
            default: 2,
        }
    ],
    extractProps: ({ attrs, options }) => {
        return {
            ...floatField.extractProps({attrs, options}),
            minDecimalPrecision: options.min_decimal_precision || 2,
        }
    }
}

registry.category("fields").add("account_min_digits", accountMinDigits);
