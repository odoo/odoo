import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";

export class RecruitmentFormController extends FormController {
    /**
     * @override
     */
    get archiveDialogProps() {
        const result = super.archiveDialogProps;
        result.body =
            this.model.root.data.all_application_count > 0
                ? _t("This job position and all related applicants will be archived. Are you sure?")
                : _t("Are you sure that you want to archive this job position?");
        console.log(this.model.root.data.all_application_count);
        return result;
    }
}
