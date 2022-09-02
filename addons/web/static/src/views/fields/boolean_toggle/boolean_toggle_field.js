/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }
}

BooleanToggleField.template = "web.BooleanToggleField";

BooleanToggleField.displayName = _lt("Toggle");

registry.category("fields").add("boolean_toggle", BooleanToggleField);
