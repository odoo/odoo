/* global posmodel */

import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { changesToOrder } from "@point_of_sale/app/models/utils/order_change";

// Return rendered kiosk prepration receipts that will be printed after order confirmation
export function generateKioskPreparationReceipt() {
    const order = posmodel.currentOrder;
    const orderData = order.getOrderData();
    const changes = changesToOrder(order, posmodel.config.preparationCategories).new;

    const printingChanges = {
        ...orderData,
        changes: {
            title: _t("NEW"),
            data: changes,
        },
    };

    return renderToElement("point_of_sale.OrderChangeReceipt", {
        data: printingChanges,
    });
}

// Validates that a receipt contains an orderline
export function hasOrderlineInReceipt(receipt, productName, qty) {
    const orderLines = Array.from(receipt.querySelectorAll(".orderline"));

    if (!orderLines.length) {
        throw new Error("No orderlines found in the receipt.");
    }

    const match = orderLines.find((line) => {
        const content = line.innerHTML;
        return (!productName || content.includes(productName)) && (!qty || content.includes(qty));
    });

    if (!match) {
        throw new Error(
            `Orderline not found for product: "${productName}"` +
                (qty ? ` with quantity: "${qty}"` : "")
        );
    }
}
