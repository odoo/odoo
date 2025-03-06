/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';

export class StockOrderpointListController extends ListController {
    async onClickOrder() {
        const resIds = await this.getSelectedResIds();
        const action = await this.model.orm.call(this.props.resModel, 'action_replenish', [resIds], {
            context: this.props.context,
        });
        if (action) {
            await this.actionService.doAction(action);
        }
        return this.actionService.doAction({
            name: "Replenishment",
            type: "ir.actions.act_window",
            res_model: "stock.warehouse.orderpoint",
            view_id: "stock.action_orderpoint_replenish",
            target: "main",
            views:[[false,'list']],
            context : {
                search_default_filter_to_reorder: true,
                search_default_filter_not_snoozed: true,
                default_trigger: 'manual',
                searchpanel_default_trigger: 'manual',
            },
        });
    }

    async onClickSnooze() {
        const resIds = await this.getSelectedResIds();
        this.actionService.doAction('stock.action_orderpoint_snooze', {
            additionalContext: { default_orderpoint_ids: resIds },
            onClose: () => {
                this.actionService.doAction('stock.action_replenishment', {
                    stackPosition: 'replaceCurrentAction',
                });
            }
        });
    }
}
