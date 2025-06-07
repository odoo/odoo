import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";

export class AccountX2ManyListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async openRecord(record) {
        const action = await this.orm.call(record.resModel, 'action_open_business_doc', [record.resId], {});
        return this.actionService.doAction(action);
    }
}

registry.category("views").add("account_x2many_list", {
    ...listView,
    Controller: AccountX2ManyListController,
});
