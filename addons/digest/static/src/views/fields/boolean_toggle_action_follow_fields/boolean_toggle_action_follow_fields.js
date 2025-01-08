import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    booleanToggleField,
    BooleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";
import { useService } from "@web/core/utils/hooks";

/**
 * Allow to define a toggle switch on a boolean readonly field that is altered using an action method.
 */
export class BooleanToggleActionFollowField extends BooleanToggleField {
    static template = "digest.BooleanToggleActionFollowField";
    static props = {
        ...BooleanToggleField.props,
        action: { type: String },
    };

    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    async onChange(newValue) {
        this.state.value = newValue;
        await this.orm.call(
            this.props.record.resModel,
            this.props.action,
            [this.props.record.resId],
            {}
        );
    }
}

export const booleanToggleFollowActionField = {
    ...booleanToggleField,
    component: BooleanToggleActionFollowField,
    displayName: _t("Toggle"),
    extractProps({ options }) {
        const props = booleanToggleField.extractProps(...arguments);
        props.action = options.action;
        if (Object.prototype.hasOwnProperty.call(options, "force_readonly")) {
            props.readonly = options.force_readonly;
        }
        return props;
    },
};

registry.category("fields").add("boolean_toggle_action_follow", booleanToggleFollowActionField);
