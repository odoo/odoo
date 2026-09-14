/** @odoo-module native */
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/fields/relational/x2many";

import { CommonSkillsListRenderer } from "../../views/skills_list_renderer.js";

export class SkillsListRenderer extends CommonSkillsListRenderer {
    static template = "hr_skills.SkillsListRenderer";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            const [skillTypeCount, historyRowCount] = await Promise.all([
                this.orm.searchCount("hr.skill.type", []),
                this.countHistoryRows(),
            ]);
            this.anySkills = skillTypeCount > 0;
            this.hasHistory = historyRowCount > 0;
        });
    }

    get employeeId() {
        const root = this.env.model.root;
        if (root.resModel === "hr.employee") {
            return root.resId;
        }
        return root.data.employee_id?.id || false;
    }

    /**
     * The history report carries its own record rules (HR users see everyone,
     * a manager their subordinates), so asking it directly answers both "may I
     * open it" and "is there anything to see" in one query.
     */
    async countHistoryRows() {
        if (this.props.list.context.no_timeline || !this.employeeId) {
            return 0;
        }
        return this.orm.searchCount("hr.employee.skill.history.report", [
            ["employee_id", "=", this.employeeId],
        ]);
    }

    get groupBy() {
        return "skill_type_id";
    }

    async skillTypesAction() {
        return this.actionService.doAction("hr_skills.hr_skill_type_action");
    }

    async openSkillsReport() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Skills Report"),
            res_model: "hr.employee.skill.history.report",
            view_mode: "graph,list",
            views: [[false, "graph"]],
            context: {
                fill_temporal: false,
            },
            target: "current",
            domain: [["employee_id", "=", this.employeeId]],
        });
    }

    get showTimeline() {
        return this.hasHistory;
    }
}

export class SkillsX2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SkillsListRenderer,
    };
    getOpenRecordTitle() {
        return this.getWizardTitleName();
    }

    getWizardTitleName() {
        return _t("Update Skills");
    }

    async onAdd({ context, editable } = {}) {
        if (this.props.record.resModel !== "hr.employee") {
            return super.onAdd({ context, editable });
        }
        return super.onAdd({
            editable,
            context: {
                ...context,
                default_employee_id: this.props.record.resId,
            },
        });
    }
}

export const skillsX2ManyField = {
    ...x2ManyField,
    component: SkillsX2ManyField,
};

registry.category("fields").add("skills_one2many", skillsX2ManyField);
