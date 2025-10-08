import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";

export const ProjectTaskModelMixin = (T) =>
    class ProjectTaskModelMixin extends T {
        _processSearchDomain(domain) {
            const { my_tasks, subtask_action } = this.env.searchModel.globalContext;
            const showSubtasks =
                my_tasks ||
                subtask_action ||
                JSON.parse(browser.localStorage.getItem("showSubtasks"));
            if (!showSubtasks) {
                domain = Domain.and([domain, [["display_in_project", "=", true]]]).toList({});
            }
            if (this.env.searchModel.context?.render_task_templates) {
                domain = Domain.and([
                    Domain.removeDomainLeaves(domain, ["has_template_ancestor"]).toList(),
                    [["has_template_ancestor", "=", true]],
                ]);
                const projectId = this.env.searchModel.context?.active_id || false;
                if (projectId) {
                    domain = Domain.and([
                        Domain.removeDomainLeaves(domain, ["project_id"]).toList(),
                        [["project_id", "in", [projectId, false]]],
                    ]);
                }
                domain = domain.toList({});
            }
            return domain;
        }
    };
