/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { PriorityField, priorityField } from "@web/views/fields/priority/priority_field";

export class PrioritySwitchField extends PriorityField {
    get commands() {
        return this.options.map(([id, name]) => [
            sprintf(this.env._t("Set priority as %s"), name),
            () => this.updateRecord(id),
            {
                category: "smart_action",
                hotkey: "alt+r",
                isAvailable: () => this.props.record.data[this.props.name] !== id,
            },
        ]);
    }
}

export const prioritySwitchField = {
    ...priorityField,
    component: PrioritySwitchField,
    extractProps({ viewType }) {
        const props = priorityField.extractProps(...arguments);
        props.withCommand = viewType === "form";
        return props;
    },
};

registry.category("fields").add("priority_switch", prioritySwitchField);
