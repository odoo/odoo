import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";

export const ProjectTaskModelMixin = (T) => class ProjectTaskModelMixin extends T {
    _processSearchDomain(domain) {
        const showTaskActions = !this.env.searchModel.globalContext.my_tasks;
        const showSubtasks = !showTaskActions || JSON.parse(browser.localStorage.getItem("showSubtasks"));
        if (!showSubtasks) {
            return Domain.and([
                domain,
                [['display_in_project', '=', true]],
            ]).toList({});
        }
        return domain;
    }
}
