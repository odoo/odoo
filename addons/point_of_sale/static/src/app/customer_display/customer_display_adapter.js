import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { toRaw } from "@odoo/owl";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const CONSOLE_COLOR = "#FF8269";

/**
 * This module provides functions to format order and order line data for customer display.
 * The goal is to format data in a way that avoids loading all models in the customer display.
 */

export class CustomerDisplayPosAdapter {
    constructor() {
        this.setup();
    }

    setup() {
        this.data = {};
        this.channel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
    }

    dispatch(pos) {
        this.channel.postMessage(JSON.parse(JSON.stringify(this.data)));
        pos.data
            .call("pos.config", "update_customer_display", [
                [pos.config.id],
                this.data,
                localStorage.getItem("device_uuid"),
            ])
            .catch((error) => {
                logPosMessage(
                    "CustomerDisplay",
                    "dispatch",
                    "Failed to update customer display",
                    CONSOLE_COLOR,
                    [error]
                );
            });
    }

    formatOrderData(order) {
        this.currency = order.currency;
        this.data = {
            finalized: order.finalized,
            general_customer_note: order.general_customer_note,
<<<<<<< b575bdc8cb71bf33a94ae2090e847bc37488364a
            amount: order.currencyDisplayPriceIncl,
            subtotal:
                order.config_id.iface_tax_included !== "total" &&
                order.prices.taxDetails.has_tax_groups &&
                order.currencyDisplayPriceExcl,
            amountTaxes: order.prices.taxDetails.has_tax_groups && order.currencyAmountTaxes,
            change: order.change && formatCurrency(order.change, order.currency),
||||||| 3eb3393c7a19de483ba3afefeb207401fe45218c
            amount: formatCurrency(order.getTotalWithTax() || 0, order.currency),
            change: order.getChange() && formatCurrency(order.getChange(), order.currency),
=======
            amount: formatCurrency(order.getTotalWithTax() || 0, order.currency),
            change: order.getChange() && formatCurrency(-order.getChange(), order.currency),
>>>>>>> 53b9245a20deac9e17eec78356371aaca0ec8add
            paymentLines: order.payment_ids.map((pl) => this.getPaymentData(pl)),
            lines: order.lines.map((l) => this.getOrderlineData(l)),
            qrPaymentData: toRaw(order.getSelectedPaymentline()?.qrPaymentData),
        };
    }

    getOrderlineData(line) {
        return {
            productId: line.product_id.id,
            taxGroupLabels: line.taxGroupLabels,
            discount: line.getDiscountStr(),
            customerNote: line.getCustomerNote() || "",
            internalNote: line.getNote() || "[]",
            productName: line.getFullProductName(),
            price: line.currencyDisplayPrice,
            qty: line.getQuantityStr().qtyStr,
            unit: line.product_id.uom_id ? line.product_id.uom_id.name : "",
            unitPrice: line.currencyDisplayPriceUnit,
            packLotLines: line.packLotLines,
            comboParent: line.combo_parent_id?.getFullProductName?.() || "",
            price_without_discount: formatCurrency(line.displayPriceNoDiscount, line.currency),
            isSelected: line.isSelected(),
        };
    }

    getPaymentData(payment) {
        return {
            name: payment.payment_method_id.name,
            amount: formatCurrency(payment.amount, this.currency),
        };
    }
}
