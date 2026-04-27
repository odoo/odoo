/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { useService } from "@web/core/utils/hooks";

import { ListController } from "@web/views/list/list_controller";

export class L10nKePosListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    displayOrders() {
        const records = this.model.root.selection;
        return (
            records.length &&
            records.some((record) => record.data.l10n_ke_order_send_status === "not_sent")
        );
    }

    async postSelectedOrders() {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        try {
            await this.orm.call(
                "pos.order",
                "action_post_selected_orders",
                [this.env, recordIds],
                {}
            );
        } finally {
            await this.model.root.load();
        }
    }
}

registry.category("views").add("l10n_ke_edi_oscu_pos_list", {
    ...listView,
    buttonTemplate: "l10n_ke_edi_oscu_pos.ListButtons",
    Controller: L10nKePosListController,
});
