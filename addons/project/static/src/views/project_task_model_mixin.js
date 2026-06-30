import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";

export const ProjectTaskModelMixin = (T) => class ProjectTaskModelMixin extends T {
    _processSearchDomain(domain) {
        const { my_tasks, subtask_action } = this.env.searchModel.globalContext;
        const showSubtasks = my_tasks || subtask_action || JSON.parse(browser.localStorage.getItem("showSubtasks"));
        if (['project.task', 'report.project.task.user'].includes(this.env.searchModel.resModel) && !showSubtasks) {
            domain = Domain.and([
                domain,
                [['display_in_project', '=', true]],
            ]).toList({});
        }
        if (this.env.searchModel.context?.render_task_templates) {
            domain = Domain.removeDomainLeaves(domain, [
                "has_template_ancestor",
                "has_project_template",
                "project_id.is_template",
            ]);
            const templateTaskDomain = Domain.or([[["has_template_ancestor", "=", true]],
                "default_project_id" in this.env.searchModel.globalContext ?
                        Domain.TRUE :
                        [["project_id.is_template", "=", true]]]);
            domain = Domain.and([domain, templateTaskDomain]).toList({});
        }
        return domain;
    }
}
