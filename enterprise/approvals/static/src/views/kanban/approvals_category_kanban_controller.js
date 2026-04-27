import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

export class ApprovalCategoryKanbanController extends KanbanController {
    async setup() {
        super.setup();
        this.action = useService("action");
    }

    OpenNewApprovalRequest() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "approval.request",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

export class ApprovalKanbanRenderer extends KanbanRenderer {
    async archiveRecord(record, active) {
        if (active) {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Are you sure that you want to archive this record?"),
                confirmLabel: _t("Archive"),
                confirm: () => {
                    record.archive();
                    this.props.list.load(); 
                },
                cancel: () => {},
            });
        } else {
            record.unarchive();
            this.props.list.load();
        }
    }
}
