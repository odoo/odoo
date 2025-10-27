import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class EventSlotListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }
    /**
     * @override
     * Open form view in dialog to ease creation and have timezone info.
     */
    async createRecord() {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("New Slot"),
                res_model: "event.slot",
                views: [[false, "form"]],
                target: "new",
            },
            {
                additionalContext: this.props.context,
                onClose: () => this.model.load(),
            }
        );
    }
}
