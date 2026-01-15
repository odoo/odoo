import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";

export const ProjectTaskAnalysisRendererMixin = (T) => class ProjectTaskAnalysisRendererMixin extends T {
    openView(domain, views, context) {
        const showSubtasks = JSON.parse(browser.localStorage.getItem("showSubtasks") || "false");
        if (!showSubtasks) {
            context.show_task_options = false;
        }
        for (const leaf of domain) {
            if (Array.isArray(leaf) && leaf[0] === "task_id") {
                leaf[0] = "id";
            }
        }
        const fieldsNotInBaseModel = ["nbr", "rating_last_value", "rating_avg", "delay_endings_days"];
        const newDomain = Domain.removeDomainLeaves(domain, fieldsNotInBaseModel).toList();

        this.actionService.doAction({
            context,
            domain: newDomain,
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
