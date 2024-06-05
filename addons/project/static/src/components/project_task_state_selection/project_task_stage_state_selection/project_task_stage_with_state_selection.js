import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

import { ProjectTaskStateSelection } from "../project_task_state_selection";


export class TaskStageWithStateSelection extends Component {
    static template = "project.TaskStageWithStateSelection";

    static props = {
        ...standardFieldProps,
        stateReadonly: { type: Boolean, optional: true },
        viewType: { type: String }
    }

    static components = {
        ProjectTaskStateSelection,
        Many2OneField,
    }

    setup() {
        this.stateProps = {
            ...(({ stateReadonly, viewType, ...o }) => o)(this.props),
            name: 'state',
            readonly: this.props.stateReadonly,
            viewType: this.props.viewType,
            showLabel: false,
        }
    }
}

export const taskStageWithStateSelection = {
    component: TaskStageWithStateSelection,
    supportedOptions: [
        {
            label: _t("State readonly"),
            name: "state_readonly",
            type: "boolean",
            default: true,
            help: _t(
                "If set, state is set to readonly."
            ),
        }
    ],
    supportedTypes: ["many2one"],
    extractProps({ options, viewType }) {
        return {
            stateReadonly: 'state_readonly' in options ? options.state_readonly : true,
            viewType: viewType,
        };
    },
};

registry.category("fields").add("task_stage_with_state_selection", taskStageWithStateSelection);
