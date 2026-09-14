/** @odoo-module native */
import { formatDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";

import { CommonSkillsListRenderer } from "../../views/skills_list_renderer.js";
import {
    SkillsX2ManyField,
    skillsX2ManyField,
} from "../skills_one2many/skills_one2many.js";

export class ResumeListRenderer extends CommonSkillsListRenderer {
    static template = "hr_skills.ResumeListRenderer";
    static rowsTemplate = "hr_skills.ResumeListRenderer.Rows";
    static recordRowTemplate = "hr_skills.ResumeListRenderer.RecordRow";
    static useMagicColumnWidths = false;

    get groupBy() {
        return "line_type_id";
    }

    get colspan() {
        if (this.props.activeActions) {
            return 3;
        }
        return 2;
    }

    buildRowApi() {
        return {
            ...super.buildRowApi(),
            formatDate,
            onLineLinkClick: (ev) => this.onLineLinkClick(ev),
        };
    }

    onLineLinkClick(ev) {
        const link = ev.target.closest("a[href]");
        if (!link) {
            return;
        }
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        ev.stopPropagation();
    }
}

export class ResumeX2ManyField extends SkillsX2ManyField {
    static components = {
        ...SkillsX2ManyField.components,
        ListRenderer: ResumeListRenderer,
    };
    getWizardTitleName() {
        return _t("New Resume Line");
    }
}

export const resumeX2ManyField = {
    ...skillsX2ManyField,
    component: ResumeX2ManyField,
};

registry.category("fields").add("resume_one2many", resumeX2ManyField);
