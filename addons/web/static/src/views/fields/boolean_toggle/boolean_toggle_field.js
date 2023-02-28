/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { booleanField, BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    static template = "web.BooleanToggleField";

    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }

    async onChange(newValue) {
        await this.props.record.update({ [this.props.name]: newValue });
        return this.props.record.save();
    }
}

export const booleanToggleField = {
    ...booleanField,
    component: BooleanToggleField,
    displayName: _lt("Toggle"),
};

registry.category("fields").add("boolean_toggle", booleanToggleField);
