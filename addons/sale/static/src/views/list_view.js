/** @odoo-module */

import { registry } from "@web/core/registry";
import { sprintf } from '@web/core/utils/strings';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class SaleListController extends ListController {
    /**
     * @override
     **/
    getActionMenuItems() {
        const actionMenuItems = super.getActionMenuItems();
        if (actionMenuItems) {
            actionMenuItems.other.push({
                description: this.env._t("Cancel quotations"),
                callback: async () => {
                    const selectedResIds = await this.getSelectedResIds();
                    let body;
                    if (this.nbSelected === 1) {
                        body = this.env._t("Are you sure you want to cancel the selected quotation ?")
                    }
                    else {
                        body = sprintf(
                            this.env._t(
                                "Are you sure you want to cancel the %(numberOfQuotation)s selected quotations ?",
                            ), {
                                numberOfQuotation: this.nbSelected,
                            },
                        )
                    }
                    const dialogProps = {
                        body: body,
                        confirmLabel: this.env._t("Cancel quotations"),
                        cancelLabel: this.env._t("Discard"),
                        title: this.env._t("Cancel quotations"),
                        confirm: () => {
                            this.model.orm.call(
                                this.props.resModel, "action_cancel", [selectedResIds], {
                                    context: {'disable_cancel_warning': true},
                                }
                            ),
                            this.actionService.switchView("list");
                        },
                        cancel: () => {},
                    };
                    this.dialogService.add(ConfirmationDialog, dialogProps);
                }
            });
        }
        return actionMenuItems;
    }
}

registry.category('views').add('sale_list', {
    ...listView,
    Controller: SaleListController,
});
