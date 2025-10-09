import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { _t } from "@web/core/l10n/translation";

export class AddPackageListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.addDialog = useOwnedDialogs();
        this.pickingId = this.props.list.context.picking_ids?.length
            ? this.props.list.context.picking_ids[0]
            : 0;
        this.locationId = this.props.list.context.location_id || 0;
        this.canAddEntirePacks = this.props.list.context?.can_add_entire_packs;
    }

    get displayRowCreates() {
        return this.canAddEntirePacks;
    }

    async add(params) {
        await this.onClickAdd();
    }

    async onClickAdd() {
        const domain = [];
        if (this.locationId) {
            domain.push(["location_id", "child_of", this.locationId]);
        }
        this.addDialog(SelectCreateDialog, {
            title: _t("Select Packages to Move"),
            noCreate: true,
            multiSelect: true,
            resModel: "stock.package",
            domain,
            context: {
                list_view_ref: "stock.stock_package_view_add_list",
            },
            onSelected: async (resIds) => {
                if (resIds.length) {
                    const done = await this.orm.call("stock.picking", "action_add_entire_packs", [
                        [this.pickingId],
                        resIds,
                    ]);
                    if (done) {
                        await this.actionService.doAction({
                            type: "ir.actions.client",
                            tag: "soft_reload",
                        });
                    }
                }
            },
        });
    }
}

registry.category("views").add("stock_add_package_list_view", {
    ...listView,
    Renderer: AddPackageListRenderer,
});
