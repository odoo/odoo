import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const cogMenuRegistry = registry.category("cogMenu");

class ConvertProjectToTemplateCogMenu extends Component {
    static template = "project.ConvertProjectToTemplateCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    toggleProjectTemplateMode() {
        this.action.doActionButton({
            type: "object",
            resId: this.env.searchModel._context.active_id,
            name: "action_toggle_project_template_mode",
            resModel: "project.project",
        });
    }
}

export const ConvertProjectToTemplateMenuItem = {
    Component: ConvertProjectToTemplateCogMenu,
    groupNumber: 10,
    isDisplayed: async ({config, searchModel}) => {
        return (
            searchModel.resModel === "project.task" &&
            ["kanban", "list"].includes(config.viewType) &&
            config.actionType === "ir.actions.act_window" &&
            searchModel._context.active_id
        );
    },
};

cogMenuRegistry.add("convert-project-to-template-menu", ConvertProjectToTemplateMenuItem);
