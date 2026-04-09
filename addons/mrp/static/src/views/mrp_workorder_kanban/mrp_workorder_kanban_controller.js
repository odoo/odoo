import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { KanbanController } from "@web/views/kanban/kanban_controller";

export class MrpWorkorderKanbanController extends KanbanController {
    async setup() {
        super.setup();
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async selectOrdersToPlan() {
        const action = await this.orm.call(this.model.config.resModel, "action_select_mo_to_plan", [false]);
        this.action.doAction(
            action,
            {
                onClose: async () => { await this.model.load(); },
            }
        );
    }

    async updatePlanning() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to Update the Planning ?"),
            confirmLabel: _t("Update"),
            confirm: async () => {
                await this.orm.call(this.model.config.resModel, "action_replan", [false])
                await this.model.load();
            },
            cancel: () => { },
        });
    }
}
