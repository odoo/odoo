import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { booleanField, BooleanField } from "../boolean/boolean_field";

export class BooleanToggleField extends BooleanField {
    static props = {
        ...BooleanField.props,
    };

    async onChange(newValue) {
        this.state.value = newValue;
        const changes = { [this.props.name]: newValue };
        await this.props.record.update(changes);
    }

    get displayAsToggle() {
        return true;
    }
}

export const booleanToggleField = {
    ...booleanField,
    component: BooleanToggleField,
    displayName: _t("Toggle"),
    additionalClasses: ["o_boolean_interactive"],
    extractProps(_, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("boolean_toggle", booleanToggleField);
