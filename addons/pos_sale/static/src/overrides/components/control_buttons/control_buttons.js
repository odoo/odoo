/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(ControlButtons.prototype, {
    onClickQuotation() {
        this.dialog.add(SelectCreateDialog, {
            resModel: "sale.order",
            multiSelect: false,
            noCreate: true,
            domain: [
                ["state", "!=", "cancel"],
                ["amount_unpaid", ">", 0],
            ],
            onSelected: async (resIds) => {
                return await this.pos.onClickSaleOrder(resIds[0]);
            },
            size: "xl",
            listViewId: this.pos.session._sale_order_tree_view_id,
            kanbanViewId: this.pos.session._sale_order_kanban_view_id,
            closeIfSelectCancel: false,
        });
    },
});
