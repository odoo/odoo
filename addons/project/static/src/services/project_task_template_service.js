import { registry } from "@web/core/registry";

class ProjectTaskTemplate {
    templateIdValue = null;

    get templateId() {
        const templateIdValue = this.templateIdValue;
        this.templateIdValue = null;
        return templateIdValue;
    }

    set templateId(templateId) {
        this.templateIdValue = templateId;
    }
}

export const projectTaskTemplateService = {
    dependencies: [],
    async start() {
        return new ProjectTaskTemplate();
    },
};

registry.category("services").add("project_task_template", projectTaskTemplateService);
