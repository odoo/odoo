export const ProjectTaskAnalysisRendererMixin = (T) =>
    class ProjectTaskAnalysisRendererMixin extends T {
        openView(domain, views, context) {
            const fieldsNotInBaseModel = ["nbr", "rating_last_value", "rating_avg", "task_id"];

            if (domain) {
                for (const leaf of domain) {
                    if (Array.isArray(leaf) && fieldsNotInBaseModel.includes(leaf[0])) {
                        return;  // early return if any unwanted field is found
                    }
                }
            }
            this.actionService.doAction(
                {
                    context,
                    domain,
                    name: "Tasks",
                    res_model: "project.task",
                    target: "current",
                    type: "ir.actions.act_window",
                    views,
                },
                {
                    viewType: "list",
                }
            );
        }
    };
