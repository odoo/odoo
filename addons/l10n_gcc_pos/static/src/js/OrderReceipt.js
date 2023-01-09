/** @odoo-module */

import OrderReceipt from "@point_of_sale/js/Screens/ReceiptScreen/OrderReceipt";
import Registries from "@point_of_sale/js/Registries";

const OrderReceiptGCC = (OrderReceipt) =>
    class extends OrderReceipt {
        get receiptEnv() {
            const receipt_render_env = super.receiptEnv;
            const receipt = receipt_render_env.receipt;
            const country = receipt_render_env.order.pos.company.country;
            receipt.is_gcc_country = ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
                country && country.code
            );
            return receipt_render_env;
        }
    };
Registries.Component.extend(OrderReceipt, OrderReceiptGCC);
export default OrderReceiptGCC;
