import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(ControlButtons.prototype, {
    onClickQuotation() {
        const context = {
            search_view_ref: "pos_sale.view_sale_order_search_inherit_pos_sale",
            list_view_ref: "pos_sale.sale_order_list_inherit_pos_sale",
            search_default_unpaid_orders_filter: true,
        };
        let domain = [
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
            ["currency_id", "=", this.pos.currency.id],
            "|",
            ["amount_unpaid", ">", 0],
            ["pos_order_line_ids", "=", false],
        ];
        if (this.partner) {
            context["search_default_partner_id"] = this.partner.id;
            domain = [...domain, ["partner_id", "any", [["id", "child_of", [this.partner.id]]]]];
        }
        this.dialog.add(SelectCreateDialog, {
            title: _t("Quotation / Order"),
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
