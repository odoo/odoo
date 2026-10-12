import { Domain } from "@web/core/domain";

export const ProjectModelMixin = (T) => class ProjectModelMixin extends T {
    _processSearchDomain(domain) {
        if (this.env.searchModel.context?.render_project_templates) {
            return Domain.and([
                Domain.removeDomainLeaves(domain, ['is_template']).toList(),
                [['is_template', '=', true]],
            ]).toList({});
        }
        return domain;
    }
}
