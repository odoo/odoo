import { Component } from "@odoo/owl";

import { registry } from '@web/core/registry';
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class IntegrationStateSelectionField extends Component {
    static template = "hr_recruitment_integration_base.IntegrationStateSelection";
    static props = {
        ...standardFieldProps,
        ribbon: { type: Boolean, optional: true },
    }
    setup() {
        super.setup();
        this.colors = {
            'pending': ["info", "info"],
            'warning': ["warning", "warning"],
            'expired': ["muted", "muted"],
            'deleted': ["muted", "secondary"],
            'failure': ["danger", "danger"],
            'success': ["success", "success"]
        };
        this.titles = {
            'pending': "pending",
            'warning': "warning",
            'expired': "expired",
            'deleted': "deleted",
            'failure': "issue",
            'success': "published",
        }
    }

    get imgClassNames() {
        return `fa fa-fw o_button_icon fa-circle${this.value == 'deleted' ? "-o" : ""} text-${this.color[0]}`
    }

    get ribbonClassNames() {
        return `text-bg-${this.color[1]}`
    }

    get color() {
        return this.colors[this.value];
    }

    get title() {
        return this.titles[this.value];
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const integrationStateSelectionField = {
    component: IntegrationStateSelectionField,
    supportedOptions: [
        {
            name: "ribbon",
            type: "boolean"
        }
    ],
    extractProps({ options }) {
        return {'ribbon': Boolean(options.ribbon)};
    },
};

registry.category("fields").add("integration_state_selection", integrationStateSelectionField);
