import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ProjectTaskKanbanQuickCreateModel extends RelationalModel {
    static services = [...RelationalModel.services, "project_task_template"];

    setup(params, { project_task_template }) {
        this.projectTaskTemplate = project_task_template;
        super.setup(...arguments);
    }

    /**
     * @override
     */
    async _loadNewRecord(config, params = {}) {
        Object.assign(config.context, {
            task_template_id: this.projectTaskTemplate.templateId,
        });
        return super._loadNewRecord(config, params);
    }
}
