import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

export class AddPackageListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.pickingId = this.props.list.context.picking_id || 0;
        this.showEntirePacks = this.props.list.context?.show_entire_packs;
    }

    get displayRowCreates() {
        return this.showEntirePacks;
    }

    async add(params) {
        if (this.displayRowCreates) {
            await this.onClickAdd();
        }
    }

    async onClickAdd(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.add.entire.packages",
            name: _t("Add a Package"),
            views: [[false, "form"]],
            target: "new",
            context: {
                "default_picking_id": this.pickingId,
            },
        }, {
            onClose: () => {
                this.actionService.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                });
            },
        });
    }
}

registry.category('views').add('stock_add_package_list_view', {
    ...listView,
    Renderer: AddPackageListRenderer,
});
