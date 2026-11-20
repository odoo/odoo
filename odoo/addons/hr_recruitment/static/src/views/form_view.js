/** @odoo-module */

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';

export class InterviewerFormController extends FormController {

    /**
     * Add `o_applicant_interviewer_form` class if necessary
     */
    get className() {
        const result = super.className;
        const root = this.model.root;
        if (!root.data.interviewer_ids || !root.data.user_id) {
            return result;
        }
        result["o_applicant_interviewer_form"] = root.data.interviewer_ids.records.findIndex(
            interviewer => interviewer.resId === root.data.user_id[0]) > -1;
        return result;
    }
}

registry.category('views').add('hr_recruitment_interviewer', {
    ...formView,
    Controller: InterviewerFormController,
});
