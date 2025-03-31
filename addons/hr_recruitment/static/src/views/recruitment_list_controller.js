import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";

export class RecruitmentListController extends ListController {
    /**
     * @override
     */
    get archiveDialogProps() {
        const result = super.archiveDialogProps;
        result.body =
            this.model.root.isDomainSelected || this.model.root.selection.length > 1
                ? _t(
                      "These job positions and all related applicants will be archived. Are you sure?"
                  )
                : _t(
                      "This job position and all related applicants will be archived. Are you sure?"
                  );
        return result;
    }
}
