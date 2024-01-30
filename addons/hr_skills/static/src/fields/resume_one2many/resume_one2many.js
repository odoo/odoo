/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { formatDate } from "@web/core/l10n/dates";

import { SkillsX2ManyField, skillsX2ManyField } from "../skills_one2many/skills_one2many";
import { CommonSkillsListRenderer } from "../../views/skills_list_renderer";

export class ResumeListRenderer extends CommonSkillsListRenderer {
    get groupBy() {
        return 'line_type_id';
    }

    get colspan() {
        if (this.props.activeActions) {
            return 3;
        }
        return 2;
    }

    formatDate(date) {
        return formatDate(date);
    }

    setDefaultColumnWidths() {}
}
ResumeListRenderer.template = 'hr_skills.ResumeListRenderer';
ResumeListRenderer.rowsTemplate = "hr_skills.ResumeListRenderer.Rows";
ResumeListRenderer.recordRowTemplate = "hr_skills.ResumeListRenderer.RecordRow";


export class ResumeX2ManyField extends SkillsX2ManyField {
    get title() {
        return _t("Select Experience");
    }
}

ResumeX2ManyField.components = {
    ...SkillsX2ManyField.components,
    ListRenderer: ResumeListRenderer,
};

export const resumeX2ManyField = {
    ...skillsX2ManyField,
    component: ResumeX2ManyField,
};

registry.category("fields").add("resume_one2many", resumeX2ManyField);
