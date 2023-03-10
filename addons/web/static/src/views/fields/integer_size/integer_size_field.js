/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatIntegerSize } from "../formatters"
import { IntegerField } from "../integer/integer_field"


export class IntegerSizeField extends IntegerField {
    get formattedValue() {
        if (!this.props.readonly && this.props.inputType === "number") {
            return this.props.value;
        }
        return formatIntegerSize(this.props.value);
    }
}

IntegerSizeField.displayName = _lt("Size");


registry.category("fields").add("integer_size", IntegerSizeField);
