import { registry } from "@web/core/registry";
import { percentageField, PercentageField } from "@web/views/fields/percentage/percentage_field";
import { parsePercentage } from "@web/views/fields/parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { formatMailingPercentage } from "../format_utils";

export class MailingPercentageField extends PercentageField {
    setup() {
        super.setup();
        useInputField({
            getValue: () =>
                formatMailingPercentage(this.props.record.data[this.props.name], {
                    digits: this.props.digits,
                    noSymbol: true,
                    field: this.props.record.fields[this.props.name],
                }),
            refName: "numpadDecimal",
            parse: (v) => parsePercentage(v),
        });
    }

    get formattedValue() {
        return formatMailingPercentage(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            field: this.props.record.fields[this.props.name],
        });
    }
}

export const mailingPercentageField = {
    ...percentageField,
    component: MailingPercentageField,
};

registry.category("fields").add("mailing-percentage", mailingPercentageField);
