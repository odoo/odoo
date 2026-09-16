import { markup, onWillStart, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

export class CertificationListRenderer extends ListRenderer {
    static template = "hr_skills.CertificationListRenderer";

    setup() {
        super.setup();
        this.certificationState = proxy({ hasCertificationSkillType: null });
        onWillStart(async () => {
            this.certificationState.hasCertificationSkillType = Boolean(
                await this.orm.searchCount("hr.skill.type", [["is_certification", "=", true]])
            );
        });
    }

    get noContentHelp() {
        if (!this.certificationState.hasCertificationSkillType) {
            return this.props.noContentHelp;
        }
        return markup(
            `<p class="o_view_nocontent_smiling_face">${_t("No Certified Employees. Register a Certification!")}</p>
            <a type="action" name="hr_skills.action_hr_employee_new_certification" class="btn btn-primary">
            ${_t("New certification")}
            </a>`
        );
    }
}

export const certificationListView = {
    ...listView,
    Renderer: CertificationListRenderer,
};

registry.category("views").add("hr_employee_skill_certification_list", certificationListView);
