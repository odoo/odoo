import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { onWillStart } from "@odoo/owl";
import { userHasEmployeeInCurrentCompany } from "@hr_holidays/utils";

export class RequestKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialogService = useService("dialog");

        this.hasEmployee = false;
        onWillStart(async () => {
            this.hasEmployee = await userHasEmployeeInCurrentCompany(this.orm);
        });
    }

    async createRecord() {
        if (!this.hasEmployee) {
            this.dialogService.add(AlertDialog, {
                title: _t("UserError"),
                body: _t("This operation is not allowed as you are not linked to an employee in the current company."),
            });
            return;
        }
        return super.createRecord();
    }
}

const RequestKanbanView = {
    ...kanbanView,
    Controller: RequestKanbanController
};

registry.category("views").add("hr_holidays_request_kanban", RequestKanbanView);
