import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";


export class AddPackageListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.pickingId = this.props.context.picking_id || 0;
        this.packageIds = this.props.context.all_package_ids || [];
    }

    async onClickAdd(ev){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.add.entire.packages",
            name: _t("Add a Package"),
            views: [[false, "form"]],
            target: "new",
            context: {
                "default_picking_id": this.pickingId,
                "default_linked_package_ids": this.packageIds,
            }
        });
    }
}

registry.category('views').add('stock_add_package_list_view', {
    ...listView,
    Controller: AddPackageListController,
    buttonTemplate: 'stock.AddPackageListView.Buttons',
});
