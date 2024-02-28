/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }
    onChange(newValue) {
        this.props.update(newValue, { save: this.props.autosave });
    }
}

BooleanToggleField.template = "web.BooleanToggleField";

BooleanToggleField.displayName = _lt("Toggle");
BooleanToggleField.props = {
    ...BooleanField.props,
    autosave: { type: Boolean, optional: true },
};
BooleanToggleField.extractProps = ({ attrs }) => {
    return {
        autosave: "autosave" in attrs.options ? Boolean(attrs.options.autosave) : true,
    };
};

registry.category("fields").add("boolean_toggle", BooleanToggleField);
