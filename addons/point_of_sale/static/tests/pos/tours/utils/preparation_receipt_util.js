/* global posmodel */

import { renderToElement } from "@web/core/utils/render";

export function generatePreparationChanges() {
    const order = posmodel.getOrder();
    const orderChange = posmodel.changesToOrder(
        order,
        posmodel.config.preparationCategories,
        false
    );

    return posmodel.generateOrderChange(
        order,
        orderChange,
        Array.from(posmodel.config.preparationCategories),
        false
    );
}

export function generatePreparationReceiptElement() {
    const { orderData, changes } = generatePreparationChanges();
    orderData.changes = {
        title: "new",
        data: changes.new,
    };

    return renderToElement("point_of_sale.OrderChangeReceipt", {
        data: orderData,
    });
}
