import { signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class ProjectTaskControlPanel extends ControlPanel {
    static template = "project.ProjectTaskControlPanel";

    setup() {
        super.setup();
        this.showSubtasksKey = "showSubtasks";
        this.showSubtasks = signal(
            JSON.parse(localStorage.getItem(this.showSubtasksKey) || "false")
        );
    }

    get showTaskOptions() {
        const context = this.env.searchModel.globalContext;
        return (
            !context.my_tasks &&
            !context.activity_action &&
            (!("show_task_options" in context) || context.show_task_options)
        );
    }

    get taskOptionsTitle() {
        if (this.env.config.hub) {
            return _t("Show sub-tasks & hub tabs");
        }
        return _t("Show sub-tasks");
    }

    onClickShowSubtasks(ev) {
        this.showSubtasks.set(!this.showSubtasks());
        localStorage.setItem(this.showSubtasksKey, this.showSubtasks());
        this.env.searchModel.search();
    }

    /**
     * Whether the hub items are listed in the task options dropdown (on small
     * screens, where the hub tabs aren't displayed).
     */
    hasMobileHubItems() {
        return (
            this.uiService.isSmall &&
            Boolean(this.env.config.hub && this.env.config.hub.items().length)
        );
    }
}
