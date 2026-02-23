import { registry } from "@web/core/registry";
import { percentageField, PercentageField } from "@web/views/fields/percentage/percentage_field";
import { parsePercentage } from "@web/views/fields/parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { formatFullRangePercentage } from "../format_utils";

/**
 * This widget allows to render values in range `[0..100]`
 * as percentages in the list view.
 * Eg: given value `49` the rendered result will be `49%`.
 *
 * The base `PercentageField` only renders values in range
 * `[0..1]` and scales them to 100.
 * Eg: given value `0.49` the rendered result will be `49%`.
 */
export class FullRangePercentageField extends PercentageField {
    setup() {
        super.setup();
        useInputField({
            getValue: () =>
                formatFullRangePercentage(this.props.record.data[this.props.name], {
                    digits: this.props.digits,
                    noSymbol: true,
                    field: this.props.record.fields[this.props.name],
                }),
            refName: "numpadDecimal",
            parse: (v) => parsePercentage(v),
        });
    }

    get formattedValue() {
        return formatFullRangePercentage(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            field: this.props.record.fields[this.props.name],
        });
    }
}

export const fullRangePercentageField = {
    ...percentageField,
    component: FullRangePercentageField,
};

registry.category("fields").add("full_range_percentage", fullRangePercentageField);
