import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { ProjectTaskStateSelection } from "../project_task_state_selection";

export class TaskStageWithStateSelection extends Component {
    static template = "project.TaskStageWithStateSelection";

    static props = {
        ...standardFieldProps,
        viewType: { type: String },
    };

    static components = {
        ProjectTaskStateSelection,
        Many2One,
    };

    get stageProps() {
        return computeM2OProps(this.props);
    }

    get stateProps() {
        return {
            ...omit(this.props, "viewType"),
            name: "state",
            viewType: this.props.viewType,
            showLabel: false,
        };
    }
}

export const taskStageWithStateSelection = {
    component: TaskStageWithStateSelection,
    fieldDependencies: [{ name: "state", type: "selection" }],
    supportedTypes: ["many2one"],
    extractProps({ viewType }) {
        return {
            viewType,
        };
    },
};

registry.category("fields").add("task_stage_with_state_selection", taskStageWithStateSelection);
