import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";

export class RecruitmentListController extends ListController {
    /**
     * @override
     */
    get archiveDialogProps() {
        const result = super.archiveDialogProps;
        result.title = _t("Archive job position")
        result.confirmLabel = _t("Archive")
        result.body =
            this.model.root.isDomainSelected || this.model.root.selection.length > 1
                ? _t(
                      "If you archive these job positions, all their applicants will be archived too. Are you sure?"
                  )
                : _t(
                      "If you archive this job position, all its applicants will be archived too. Are you sure?"
                  );
        return result;
    }
}
