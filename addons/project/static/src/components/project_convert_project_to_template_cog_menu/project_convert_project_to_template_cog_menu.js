import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";

const cogMenuRegistry = registry.category("cogMenu");

class ConvertProjectToTemplateCogMenu extends Component {
    static template = "project.ConvertProjectToTemplateCogMenu";
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
    }

    toggleProjectTemplateMode() {
        this.action.doActionButton({
            type: "object",
            resId: this.env.searchModel.context.active_id,
            name: "action_toggle_project_template_mode",
            resModel: "project.project",
        });
    }
}

export const ConvertProjectToTemplateMenuItem = {
    Component: ConvertProjectToTemplateCogMenu,
    groupNumber: 0,
    async isDisplayed() {
        const env = useEnv();
        return (
            env.searchModel.resModel === "project.task" &&
            ["kanban", "list"].includes(env.config.viewType) &&
            env.config.actionType === "ir.actions.act_window" &&
            env.searchModel.context.active_id &&
            await user.hasGroup("project.group_project_manager")
        );
    },
};

cogMenuRegistry.add("convert-project-to-template-menu", ConvertProjectToTemplateMenuItem);
