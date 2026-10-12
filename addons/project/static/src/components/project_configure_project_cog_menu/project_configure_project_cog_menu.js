import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";

const cogMenuRegistry = registry.category("cogMenu");

class ConfigureProjectCogMenu extends Component {
    static template = "project.ConfigureProjectCogMenu";
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
    }

    openProjectForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "project.project",
            res_id: this.env.searchModel.context.active_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

export const ConfigureProjectMenuItem = {
    Component: ConfigureProjectCogMenu,
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

cogMenuRegistry.add("configure-project-menu", ConfigureProjectMenuItem);
