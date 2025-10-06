import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class BomLineListController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async openRecord(record) {
        await this.action.doAction({
            res_model: "mrp.bom",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: record.data.bom_id.id,
            target: "current",
        });
    }
}

registry.category("views").add("bom_line_list", {
    ...listView,
    Controller: BomLineListController,
});
