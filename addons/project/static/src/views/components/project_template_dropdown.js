import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ProjectTemplateDropdown extends Component {
    static template = "project.ProjectTemplateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };

    static props = {
        hotkey: {
            type: String,
            optional: true,
        },
        newButtonClasses: String,
        onCreate: Function,
        context: Object,
        getAdditionalContext: {
            type: Function,
            optional: true,
        },
        isDisabled: {
            type: Boolean,
            optional: true,
        },
    };
    static defaultProps = {
        hotkey: "r",
        isDisabled: false,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
        this.projectTemplates = [];
    }

    get readFields() {
        return ["id", "name"];
    }

    get projectTemplatesDomain() {
        return [["is_template", "=", true]];
    }

    async onWillStart() {
        this.projectTemplates = await this.orm.searchRead(
            "project.project",
            this.projectTemplatesDomain,
            this.readFields
        );
    }

    contextPreprocess(templateId) {
        const context = { ...this.props.context };
        if (this.props.getAdditionalContext) {
            Object.assign(context, this.props.getAdditionalContext());
        }
        return context;
    }

    async createProjectFromTemplate(template) {
        const { id: templateId, name: templateName } = template;
        const action = await this.orm.call(
            "project.template.create.wizard",
            "action_open_template_view",
            [],
            {
                context: {
                    ...this.contextPreprocess(templateId),
                    template_id: templateId,
                    template_name: templateName,
                },
            }
        );
        this.action.doAction(action);
    }
}
