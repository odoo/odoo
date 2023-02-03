/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { PriorityField, priorityField } from "@web/views/fields/priority/priority_field";
import { useCommand } from "@web/core/commands/command_hook";
import { useState } from "@odoo/owl";

export class PrioritySwitchField extends PriorityField {
    setup() {
        this.state = useState({
            index: -1,
        });
        if (this.props.record.activeFields[this.props.name].viewType !== "form") {
            return;
        }

        for (const [id, name] of this.options) {
            useCommand(
                sprintf(this.env._t("Set priority as %s"), name),
                () => this.props.update(id),
                {
                    category: "smart_action",
                    hotkey: "alt+r",
                    isAvailable: () => this.props.value !== id,
                }
            );
        }
    }
}

export const prioritySwitchField = {
    ...priorityField,
    component: PrioritySwitchField,
};

registry.category("fields").add("priority_switch", prioritySwitchField);
