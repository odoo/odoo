import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";

export class RecruitmentFormController extends FormController {
    /**
     * @override
     */
    get archiveDialogProps() {
        const result = super.archiveDialogProps;
        result.title = _t("Archive job position")
        result.confirmLabel = _t("Archive")
        result.body =
            this.model.root.data.all_application_count > 0
                ? _t("If you archive this job position, all its applicants will be archived too. Are you sure?")
                : _t("Are you sure that you want to archive this job position?");
        return result;
    }
}
