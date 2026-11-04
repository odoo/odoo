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
            // A down payment still has to be deducted when settling the order,
            // settling deducts it with a negative PoS line
            "|",
            ["amount_unpaid", ">", 0],
            "&",
            ["order_line.is_downpayment", "=", true],
            [
                "order_line",
                "not any",
                [
                    ["is_downpayment", "=", true],
                    [
                        "pos_order_line_ids",
                        "any",
                        [
                            ["qty", "<", 0],
                            ["order_id.state", "not in", ["cancel", "draft"]],
                        ],
                    ],
                ],
            ],
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
