/** @odoo-module native */
import { _t } from "@web/core/translation";
import { FormController } from "@web/views/form";

export class RecruitmentFormController extends FormController {
    /** @override */
    get archiveDialogProps() {
        const result = super.archiveDialogProps;
        // The cascade archives the *running* applications; a refused one is
        // already archived and will not move, so `all_application_count` --
        // which counts those too -- promised a cascade that would not happen.
        result.body =
            this.model.root.data.application_count > 0
                ? _t(
                      "This job position and all related applicants will be archived. Are you sure?",
                  )
                : _t("Are you sure that you want to archive this job position?");
        return result;
    }
}
