import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(OrderReceipt.prototype, {
    getTaxDetails(taxGroups) {
        if (this.props.data.headerData.company.country_id?.code !== "IN") {
            return super.getTaxDetails(taxGroups);
        }
        return this.props.data.tax_details.map((tax_group) => {
            let tax_name = tax_group.name;
            if (this.props.data.taxTotals.same_tax_base && this.props.data.tax_details.length > 2) {
                tax_name += " on " + this.props.formatCurrency(tax_group.base);
            }
            return {
                ...taxGroups,
                id: tax_group.id,
                tax_name: tax_name,
                group_label: tax_group.tax_group_id.pos_receipt_label,
                tax_amount_currency: tax_group.amount,
            };
        });
    },
});
