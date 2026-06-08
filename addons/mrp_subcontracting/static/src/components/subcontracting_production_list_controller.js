import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class SubcontractingProductionListController extends ListController {
    get actionMenuItems() {
        let items = super.actionMenuItems;
        items.action = []
        return items;
    }
}

registry.category("views").add("subcontracting_production_list", {
    ...listView,
    Controller: SubcontractingProductionListController,
});
