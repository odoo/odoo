/** @odoo-module */

import { registry } from "@web/core/registry";

import { formatDate } from "@web/core/l10n/dates";

import { SkillsX2ManyField } from "./skills_one2many";
import { CommonSkillsListRenderer } from "../views/skills_list_renderer";

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

    get RowsTemplate() {
        return 'hr_skills.ResumeListRenderer.Rows';
    }

    get RecordRowTemplate() {
        return 'hr_skills.ResumeListRenderer.RecordRow';
    }
}
ResumeListRenderer.template = 'hr_skills.ResumeListRenderer';

export class ResumeX2ManyField extends SkillsX2ManyField {
    setup() {
        super.setup();
        this.Renderer = ResumeListRenderer;
    }
}

registry.category("fields")
    .add("resume_one2many", ResumeX2ManyField);
