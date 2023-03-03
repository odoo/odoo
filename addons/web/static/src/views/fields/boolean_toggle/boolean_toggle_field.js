/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { evalDomain } from "@web/views/utils";
import { booleanField, BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    static template = "web.BooleanToggleField";
    static props = {
        ...BooleanField.props,
        readonlyFromModifiers: { type: Array | Boolean, optional: true },
    };

    get isReadonly() {
        return evalDomain(this.props.readonlyFromModifiers, this.props.record.evalContext) || false;
    }

    async onChange(newValue) {
        await this.props.record.update({ [this.props.name]: newValue });
        const rootRecord =
            this.props.record.model.root instanceof this.props.record.constructor &&
            this.props.record.model.root;
        const isInEdition = rootRecord ? rootRecord.isInEdition : this.props.record.isInEdition;
        // We save only if we're on view mode readonly and no readonly field modifier
        if (!isInEdition) {
            return this.props.record.save();
        }
    }
}

export const booleanToggleField = {
    ...booleanField,
    component: BooleanToggleField,
    displayName: _lt("Toggle"),
    extractProps: (fieldInfo) => ({
        readonlyFromModifiers: fieldInfo.modifiers.readonly,
    }),
};

registry.category("fields").add("boolean_toggle", booleanToggleField);
