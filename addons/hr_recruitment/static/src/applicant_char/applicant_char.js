import { usePlugin } from "@odoo/owl";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class ApplicantCharField extends CharField {
    static template = "hr_recruitment.ApplicantCharField";

    action = usePlugin(ActionPlugin);

    onClick() {
        const record = this.props.record.data;
        if (record.res_id && record.res_model == 'hr.applicant') {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'hr.applicant',
                res_id: record.res_id.resId,
                views: [[false, "form"]],
                view_mode: "form",
                target: "current",
            });
        }
    }
}

export const applicantCharField = {
    ...charField,
    component: ApplicantCharField,
};

registry.category("fields").add("applicant_char", applicantCharField);
