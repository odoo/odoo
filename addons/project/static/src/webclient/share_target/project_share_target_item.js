import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { registry } from "@web/core/registry";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ProjectShareTargetItem extends ShareTargetItem {
    static name = _t("Task");
    static sequence = 5;
    static template = "project.ShareTargetItem";

    setup() {
        super.setup();
        this.defaultDomain = [["is_template", "=", false]];
        onWillStart(() => this.updateProjects());
    }

    get defaultState() {
        return { ...super.defaultState, projects: [], selected_project_id: false };
    }

    get hasMultiProjects() {
        return this.state.projects.length > 1;
    }

    get modelName() {
        return "project.task";
    }

    onCompanyChange(companyId) {
        super.onCompanyChange(companyId);
        this.updateProjects();
    }

    async updateProjects() {
        this.state.projects = await this.orm.webSearchRead("project.project", this.defaultDomain, {
            specification: { id: {}, display_name: {} },
            context: this.context,
        }).then(({ records }) => records);
        this.state.selected_project_id = this.state.projects.length ? this.state.projects[0] : false;
    }

    get context() {
        return {
            ...super.context,
            default_project_id: this.state.selected_project_id && this.state.selected_project_id.id,
        };
    }

    get projectRecordProps() {
        return {
            mode: "readonly",
            values: { project: this.state.selected_project_id },
            fieldNames: ["project"],
            fields: {
                project: {
                    name: "project",
                    type: "many2one",
                    relation: "project.project",
                    domain: this.defaultDomain,
                },
            },
            hooks: {
                onRecordChanged: (record) => {
                    this.state.selected_project_id = record.data.project;
                },
            },
        };
    }
}

registry.category("share_target_items").add("project", ProjectShareTargetItem);
