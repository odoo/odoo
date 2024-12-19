export const ProjectTaskAnalysisRendererMixin = (T) => class ProjectTaskAnalysisRendererMixin extends T {
    openView(domain, views, context) {
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
