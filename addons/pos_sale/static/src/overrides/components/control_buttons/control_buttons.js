/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(ControlButtons.prototype, {
    onClickQuotation() {
        let domain = [
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
            ["currency_id", "=", this.pos.currency.id],
            ["amount_unpaid", ">", 0],
        ];
        if (this.pos.get_order()?.get_partner()) {
            domain = [
                ...domain,
                [
                    "partner_id",
                    "any",
                    [["id", "child_of", [this.pos.get_order().get_partner().id]]],
                ],
            ];
        }
        this.dialog.add(SelectCreateDialog, {
            resModel: "sale.order",
            noCreate: true,
            multiSelect: false,
            domain,
            onSelected: async (resIds) => {
                await this.pos.onClickSaleOrder(resIds[0]);
            },
        });
    },
});
