/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { ListController } from "@web/views/list/list_controller";

export class InventoryReportListController extends ListController {
    get actionMenuItems() {
        const actionMenus = super.actionMenuItems;
        if (
            this.props.resModel === "stock.quant" &&
            (!this.props.context.inventory_mode || this.props.context.inventory_report_mode)
        ) {
            // hack so we don't show some of the default actions when it's inappropriate to
            const { print, action } = actionMenus;
            return {
                action: action.filter((a) => a.name !== _t("Set")),
                print: print.filter((a) => a.name !== _t("Count Sheet")),
            };
        }
        return actionMenus;
    }

    /**
     * Handler called when the user clicked on the 'Apply all' button.
     */
    async onClickApplyAll() {
        const activeIds = await this.model.orm.search(this.props.resModel, this.props.domain, {
            limit: session.active_ids_limit,
            context: this.props.context,
        });
        return this.actionService.doAction("stock.action_stock_inventory_adjustement_name", {
            additionalContext: {
                active_ids: activeIds,
            },
            onClose: () => {
                this.model.load();
            },
        });
    }
}
