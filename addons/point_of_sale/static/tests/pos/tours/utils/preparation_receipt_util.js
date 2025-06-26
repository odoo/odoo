/* global posmodel */

import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

export async function generateReceiptsToPrint(order, orderChange) {
    const { orderData, changes } = posmodel.generateOrderChange(
        order,
        orderChange,
        Array.from(posmodel.config.preparationCategories),
        false
    );
    const receiptsData = await posmodel.generateReceiptsDataToPrint(
        orderData,
        changes,
        orderChange
    );
    const groupedReceiptsData = await posmodel.prepareReceiptGroupedData(receiptsData);
    return groupedReceiptsData.map((data) =>
        renderToElement("point_of_sale.OrderChangeReceipt", {
            data: data,
        })
    );
}

// Return rendered order change receipts that will be printed when clicking "Order" button
export async function generatePreparationReceipts() {
    const order = posmodel.getOrder();
    const orderChange = posmodel.changesToOrder(
        order,
        posmodel.config.preparationCategories,
        false
    );
    return await generateReceiptsToPrint(order, orderChange);
}

// Return rendered fire course receipts that will be printed when clicking "Fire course" button
export async function generateFireCourseReceipts() {
    const order = posmodel.getOrder();
    const course = order.getSelectedCourse();
    const orderChange = {
        new: [],
        cancelled: [],
        noteUpdate: course.lines.map((line) => ({ product_id: line.getProduct().id })),
        noteUpdateTitle: _t("Course %s fired", "" + course.index),
        printNoteUpdateData: false,
    };
    return await generateReceiptsToPrint(order, orderChange);
}
