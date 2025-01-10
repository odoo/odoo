import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { omit } from "@web/core/utils/objects";

export class OrderReceipt extends Component {
    static template = "point_of_sale.OrderReceipt";
    static components = {
        Orderline,
        OrderWidget,
        ReceiptHeader,
    };
    static props = {
        data: Object,
        formatCurrency: Function,
        basic_receipt: { type: Boolean, optional: true },
    };
    static defaultProps = {
        basic_receipt: false,
    };
    omit(...args) {
        return omit(...args);
    }
    doesAnyOrderlineHaveTaxLabel() {
        return this.props.data.orderlines.some((line) => line.taxGroupLabels);
    }
    getPortalURL() {
        return `${this.props.data.base_url}/pos/ticket`;
    }

    getTaxDetails(taxGroups) {
        return taxGroups.map((tax_group) => {
            let tax_name = tax_group.group_name;
            if (!this.props.data.taxTotals.same_tax_base) {
                tax_name += " on " + this.props.formatCurrency(tax_group.base_amount);
            }
            return {
                id: tax_group.id,
                tax_name: tax_name,
                group_label: tax_group.group_label,
                tax_amount_currency: tax_group.tax_amount_currency,
            };
        });
    }
}
