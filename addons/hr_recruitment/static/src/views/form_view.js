/** @odoo-module */

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';
import { onWillStart } from "@odoo/owl";
import { useService } from '@web/core/utils/hooks';

export class InterviewerFormController extends FormController {

    setup() {
        super.setup();
        this.user = useService("user");
        onWillStart(async () => {
            this.isInterviewer = await this.user.hasGroup("hr_recruitment.group_hr_recruitment_interviewer");
        });
    }
    /**
     * Add `o_applicant_interviewer_form` class if necessary
     */
    get className() {
        const result = super.className;
        const root = this.model.root;
        if (!root.data.interviewer_ids || !root.data.user_id) {
            return result;
        }
        result["o_applicant_interviewer_form"] = this.isInterviewer
        return result;
    }
}

registry.category('views').add('hr_recruitment_interviewer', {
    ...formView,
    Controller: InterviewerFormController,
});
