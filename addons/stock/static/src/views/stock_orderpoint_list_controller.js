import { ListController } from '@web/views/list/list_controller';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class StockOrderpointListController extends ListController {
    static template = "stock.StockOrderpoint.listView";

    static components = {
        ...super.components,
        Dropdown,
        DropdownItem,
    }

    get nbSelected() {
        return this.model.root.selection.length;
    }

    async onClickOrder(force_to_max) {
        const resIds = await this.model.root.getResIds(true);
        const action = await this.model.orm.call(this.props.resModel, 'action_replenish', [resIds], {
            context: this.props.context,
            force_to_max: force_to_max,
        });
        if (action) {
            await this.actionService.doAction(action);
        }
        return this.actionService.doAction({type: 'ir.actions.client', tag: 'reload'});
    }

    async onClickSnooze() {
        const resIds = await this.model.root.getResIds(true);
        return this.actionService.doAction('stock.action_orderpoint_snooze', {
            additionalContext: { default_orderpoint_ids: resIds },
            onClose: () => { this.actionService.doAction({type: 'ir.actions.client', tag: 'reload'}); },
        });
    }
}
