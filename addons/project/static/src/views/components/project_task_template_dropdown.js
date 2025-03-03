import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ProjectTaskTemplateDropdown extends Component {
    static template = "project.TemplateDropdown";

    static props = {
        hotkey: {
            type: String,
            optional: true,
        },
        newButtonClasses: String,
        onCreate: Function,
        // Can be a number, false (in to-do) or undefined
        projectId: {
            type: [Number, Boolean],
            optional: true,
        },
    };
    static defaultProps = {
        hotkey: "r",
        projectId: null,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
        this.taskTemplates = [];
    }

    async onWillStart() {
        if (this.props.projectId) {
            this.taskTemplates = await this.orm.call("project.project", "get_template_tasks", [
                this.props.projectId,
            ]);
        }
    }

    async createTaskFromTemplate(templateId) {
        this.action.doAction(
            this.orm.call("project.task", "action_create_from_template", [templateId])
        );
    }
}
