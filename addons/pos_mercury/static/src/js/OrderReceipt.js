/** @odoo-module */

import OrderReceipt from "@point_of_sale/js/Screens/ReceiptScreen/OrderReceipt";
import Registries from "@point_of_sale/js/Registries";

const PosMercuryOrderReceipt = (OrderReceipt) =>
    class extends OrderReceipt {
        /**
         * The receipt has signature if one of the paymentlines
         * is paid with mercury.
         */
        get hasPosMercurySignature() {
            for (const line of this.paymentlines) {
                if (line.mercury_data) {
                    return true;
                }
            }
            return false;
        }
    };

Registries.Component.extend(OrderReceipt, PosMercuryOrderReceipt);

export default OrderReceipt;
