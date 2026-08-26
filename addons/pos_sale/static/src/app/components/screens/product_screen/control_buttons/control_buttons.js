import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(ControlButtons.prototype, {
    onClickQuotation() {
        const context = {};
        if (this.partner) {
            context["search_default_partner_id"] = this.partner.id;
        }

        let domain = [
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
            ["currency_id", "=", this.pos.currency.id],
            ["amount_unpaid", ">", 0],
        ];
        if (this.pos.getOrder()?.getPartner()) {
            domain = [
                ...domain,
                ["partner_id", "any", [["id", "child_of", [this.pos.getOrder().getPartner().id]]]],
            ];
        }
        const saleOrderIds = this.pos
            .getOrder()
            ?.lines?.map((l) => l.sale_order_origin_id?.id)
            .filter(Boolean);
        if (saleOrderIds?.length) {
            domain = [...domain, ["id", "not in", saleOrderIds]];
        }

        this.dialog.add(SelectCreateDialog, {
            resModel: "sale.order",
            noCreate: true,
            multiSelect: false,
            domain,
            context: context,
            onSelected: async (resIds) => {
                await this.pos.onClickSaleOrder(resIds[0]);
            },
        });
    },
});
