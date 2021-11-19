/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2OneField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get displayName() {
        return this.props.value ? this.props.value[1] : "";
    }

    async onClick() {
        const action = await this.orm.call(
            this.props.record.fields[this.props.name].relation,
            "get_formview_action",
            [[this.props.value[0]]],
            {
                /* context: this.props.record.context */
            }
        );
        await this.action.doAction(action);
    }
}

Many2OneField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
Many2OneField.template = "web.Many2OneField";

registry.category("fields").add("many2one", Many2OneField);
