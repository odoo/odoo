import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { onMounted, onPatched, Resource } from "@odoo/owl";

import { formatDate } from "@web/core/l10n/dates";

import { SkillsX2ManyField, skillsX2ManyField } from "../skills_one2many/skills_one2many";
import { CommonSkillsListRenderer } from "../../views/skills_list_renderer";

export class ResumeListRenderer extends CommonSkillsListRenderer {
    static template = "hr_skills.ResumeListRenderer";
    static rowsTemplate = "hr_skills.ResumeListRenderer.Rows";
    static recordRowTemplate = "hr_skills.ResumeListRenderer.RecordRow";
    static useMagicColumnWidths = false;
    linkRef = new Resource({ name: "link-target-blank" });

    setup() {
        super.setup();

        onMounted(this._setLinksToOpenInNewTab);
        onPatched(this._setLinksToOpenInNewTab);
    }
    get groupBy() {
        return "line_type_id";
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

    _setLinksToOpenInNewTab() {
        // Find all links within the resume descriptions and set target to "_blank"
        for (const resumeLines of this.linkRef.items()) {
            const links = resumeLines.querySelectorAll("a");

            links.forEach((link) => {
                link.setAttribute("target", "_blank"); // Set target="_blank" to open links in new tab
            });
        }
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
