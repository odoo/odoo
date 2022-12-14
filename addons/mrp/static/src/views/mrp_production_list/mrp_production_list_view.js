/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";

export class MrpProductionListController extends ListController {

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "action_cancel") {
            const proceed = await new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    body: this.env._t("Are you sure you want to cancel the manufacturing order(s) ?"),
                    cancel: () => resolve(false),
                    close: () => resolve(false),
                    confirm: () => resolve(true),
                });
            });
            if (!proceed) {
                return false;
            }
        }
        return super.beforeExecuteActionButton(clickParams);
    }
}

export const MrpProductionListView = {
    ...listView,
    Controller: MrpProductionListController,
};

registry.category("views").add('mrp_production_list', MrpProductionListView);
