import { browser } from "@web/core/browser/browser";

export const ProjectTaskAnalysisRendererMixin = (T) => class ProjectTaskAnalysisRendererMixin extends T {
    openView(domain, views, context) {
        const showSubtasks = JSON.parse(browser.localStorage.getItem("showSubtasks") || "false");
        if (!showSubtasks) {
            context.show_task_options = false;
        }
        this.actionService.doAction({
            context,
            domain,
            name: "Tasks",
            res_model: "project.task",
            target: "current",
            type: "ir.actions.act_window",
            views,
        }, {
            viewType: "list",
        });
    }
}
