import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

export class AddPackageListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.pickingId = this.props.list.context.picking_id || 0;
    }

    get displayRowCreates() {
        // As this view is not a Many2Many, this would be false otherwise.
        return true;
    }

    async add(params) {
        await this.onClickAdd();
    }

    async onClickAdd() {
        const action = await this.orm.call("stock.move", "action_add_packages", [[]], {
            context: { picking_id: this.pickingId },
        });
        this.actionService.doAction(action, {
            onClose: () => {
                this.actionService.doAction({
                    type: "ir.actions.client",
                    tag: "soft_reload",
                });
            },
        });
    }
}

registry.category("views").add("stock_add_package_list_view", {
    ...listView,
    Renderer: AddPackageListRenderer,
});
