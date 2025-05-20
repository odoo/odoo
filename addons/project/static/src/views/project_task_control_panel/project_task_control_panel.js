import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class ProjectTaskControlPanel extends ControlPanel {
    static template = "project.ProjectTaskControlPanel";

    setup() {
        super.setup();
        this.showSubtasksKey = "showSubtasks";
        this.state.showSubtasks = JSON.parse(browser.localStorage.getItem(this.showSubtasksKey) || "false");
    }

    get showTaskOptions() {
        const context = this.env.searchModel.globalContext;
        return !context.my_tasks && (!('show_task_options' in context) || context.show_task_options);
    }

    get taskOptionsTitle() {
        if (this.state.embeddedInfos.embeddedActions?.length) {
            return _t("Show sub-tasks & top menu");
        }
        return _t("Show sub-tasks");
    }

    onClickShowSubtasks(ev) {
        this.state.showSubtasks = !this.state.showSubtasks;
        browser.localStorage.setItem(this.showSubtasksKey, this.state.showSubtasks);
        this.env.searchModel.search();
    }
}
