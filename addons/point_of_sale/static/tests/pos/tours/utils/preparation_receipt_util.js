/* global posmodel */

import { renderToElement } from "@web/core/utils/render";

export function generatePreparationReceiptElement() {
    const order = posmodel.getOrder();
    const orderChange = posmodel.changesToOrder(
        order,
        posmodel.config.preparationCategories,
        false
    );

    const { orderData, changes } = posmodel.generateOrderChange(
        order,
        orderChange,
        Array.from(posmodel.config.preparationCategories),
        false
    );

    orderData.changes = {
        title: "new",
        data: changes.new,
    };

    return renderToElement("point_of_sale.OrderChangeReceipt", {
        data: orderData,
    });
}
