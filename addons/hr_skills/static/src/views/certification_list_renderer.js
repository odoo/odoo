import { markup, onWillStart, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";

// The certification-type check must be redone live every time this view is (re)mounted,
// including when the user navigates back to it through the breadcrumb: at that point the
// window action is only restored from the client-side action stack, never re-dispatched, so
// anything decided once in Python at the initial dispatch (e.g. the action's `help` or
// `context`) would otherwise stay stale even though the DB state changed in the meantime
// (typically: the user just created a certification-type Skill Type from this same screen).
async function hasCertificationSkillType(orm) {
    return Boolean(await orm.searchCount("hr.skill.type", [["is_certification", "=", true]]));
}

export class CertificationListController extends ListController {
    setup() {
        super.setup();
        this.certificationState = proxy({ hasCertificationSkillType: null });
        onWillStart(async () => {
            this.certificationState.hasCertificationSkillType = await hasCertificationSkillType(this.orm);
        });
    }

    // The "New" header button's `invisible="not context.get('show_certificate')"` is kept
    // as a stable marker for this override, not as a real context key: it is decided here,
    // live, instead of from the action's (potentially stale) context.
    evalViewModifier(modifier) {
        if (modifier === "not context.get('show_certificate')") {
            return !this.certificationState.hasCertificationSkillType;
        }
        return super.evalViewModifier(modifier);
    }
}

export class CertificationListRenderer extends ListRenderer {
    static template = "hr_skills.CertificationListRenderer";

    setup() {
        super.setup();
        this.certificationState = proxy({ hasCertificationSkillType: null, isHrManager: null });
        onWillStart(async () => {
            [
                this.certificationState.hasCertificationSkillType,
                this.certificationState.isHrManager,
            ] = await Promise.all([
                hasCertificationSkillType(this.orm),
                user.hasGroup("hr.group_hr_manager"),
            ]);
        });
    }

    // The base getter gates on `this.props.noContentHelp`, which is never set anymore: the
    // message is always decided live, below, regardless of what the action itself carries.
    get showNoContentHelper() {
        const { model } = this.props.list;
        return model.useSampleModel || !model.hasData();
    }

    get noContentHelp() {
        if (this.certificationState.hasCertificationSkillType) {
            return markup(
                `<p class="o_view_nocontent_smiling_face">${_t("No Certified Employees. Register a Certification!")}</p>
                <a type="action" name="hr_skills.action_hr_employee_new_certification" class="btn btn-primary">
                ${_t("New certification")}
                </a>`
            );
        }
        if (this.certificationState.isHrManager) {
            return markup(
                `<p class="o_view_nocontent_smiling_face">${_t("No Certifications available. Navigate to Skill types!")}</p>
                <a type="action" name="hr_skills.hr_skill_type_action" class="btn btn-primary">
                ${_t("Show Skill Types")}
                </a>`
            );
        }
        return markup(
            `<p class="o_view_nocontent_smiling_face">${_t("No Certifications available!")}</p>`
        );
    }
}

export const certificationListView = {
    ...listView,
    Controller: CertificationListController,
    Renderer: CertificationListRenderer,
};

registry.category("views").add("hr_employee_skill_certification_list", certificationListView);
