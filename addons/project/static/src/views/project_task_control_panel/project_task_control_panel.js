import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";

export class ProjectTaskControlPanel extends ControlPanel {
    static template = "project.ProjectTaskControlPanel";

    setup() {
        super.setup();
        this.showSubtasksKey = "showSubtasks";
        this.embeddedPanelState.showSubtasks = JSON.parse(
            browser.localStorage.getItem(this.showSubtasksKey) || "false"
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
        if (this.embeddedPanelState.embeddedInfos.embeddedActions?.length) {
            return _t("Show sub-tasks & top menu");
        }
        return _t("Show sub-tasks");
    }

    onClickShowSubtasks(ev) {
        this.embeddedPanelState.showSubtasks = !this.embeddedPanelState.showSubtasks;
        browser.localStorage.setItem(this.showSubtasksKey, this.embeddedPanelState.showSubtasks);
        this.env.searchModel.search();
    }

    getDropdownClass(action) {
        return (!this.env.isSmall && this.embeddedPanelState.isEmbeddedActionVisible(action)) ||
            (this.env.isSmall &&
                this.embeddedPanelState.embeddedInfos.currentEmbeddedAction?.id === action.id)
            ? "selected"
            : "";
    }
}
