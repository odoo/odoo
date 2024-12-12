import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { renderToElement } from "@web/core/utils/render";

/**
 * @typedef {Object} ReceiptData
 * @property {boolean} [reprint] - Indicates if the receipt is a duplicate.
 * @property {string} [preset_name] - The name of the preset for the receipt.
 * @property {string} config_name - The name of the POS configuration.
 * @property {string} time - The timestamp of the transaction.
 * @property {string} employee_name - The name of the employee handling the transaction.
 * @property {string} pos_reference - The order reference number.
 * @property {string} [tracking_number] - The tracking number if applicable.
 * @property {Object} changes - Contains details of order changes.
 * @property {string} changes.title - Title for the changes section.
 * @property {Array<Object>} [changes.data] - List of individual changes.
 * @property {Array<Object>} [changes.groupedData] - Grouped order changes.
 * @property {string} [internal_note] - Internal notes related to the order.
 * @property {string} [general_customer_note] - General customer notes.
 */

/**
 * @typedef {Object} OrderChangeLine
 * @property {number} quantity - The quantity of the item.
 * @property {string} display_name - The name of the product.
 * @property {boolean} [isCombo] - Indicates if the item is part of a combo.
 * @property {string[]} [attribute_value_names] - List of product attribute values.
 * @property {string} [note] - Additional note related to the product.
 */

const { DateTime } = luxon;
export class PosPreparationOrder extends Base {
    static pythonModel = "pos.preparation.order";

    /**
     * @returns {ReceiptData}
     */
    getDataForOrderChangeReceipts(printer) {
        // const applicableChanges = this.preparation_line_ids.filter((line) =>
        //     line.pos_orderline_id.product_id.product_template_id.parentPosCategIds.any((c) =>
        //         printer.product_categories_ids.includes(c)
        //     )
        // );
        const applicableChanges = this.preparation_line_ids;
        const reprint = false; // TODO
        const order = this.order_id;
        // const data = (lines, title) => ({
        //     changes: {
        //         title: title, // TODO: "NEW" or "CANCELLED" or "NOTE UPDATE"
        //         data: lines.map((preparation_line) => ({
        //             quantity: preparation_line.qty,
        //             display_name: preparation_line.pos_orderline_id.product_id.display_name,
        //             isCombo: preparation_line.pos_orderline_id.is_combo,
        //             attribute_value_names:
        //                 preparation_line.pos_orderline_id.attribute_value_ids.map(
        //                     (attr) => attr.name
        //                 ),
        //             note: preparation_line.note,
        //         })),
        //     },
        // });

        // const newLines = applicableChanges.filter((line) => line.qty > 0);
        // const cancelledLines = applicableChanges.filter((line) => line.qty < 0);
        // const noteUpdateLines = applicableChanges.filter((line) => line.qty === 0);
        // const results = [];
        // if (newLines.length) {
        //     results.push(data(newLines, "NEW"));
        // }
        // if (cancelledLines.length) {
        //     results.push(data(cancelledLines, "CANCELLED"));
        // }
        // if (noteUpdateLines.length) {
        //     results.push(data(noteUpdateLines, "NOTE UPDATE"));
        // }
        // TODO
        // if (orderChange.internal_note || orderChange.general_customer_note) {
        //     orderData.changes = {};
        //     const result = await this.printOrderChanges(orderData, printer);
        return {
            baseData: {
                reprint: reprint,
                pos_reference: order.getName(),
                config_name: order.config_id.name,
                write_date: DateTime.fromSQL(order.write_date).toFormat("HH:mm"),
                tracking_number: order.tracking_number,
                preset_name: order.preset_id?.name || "",
                employee_name: order.employee_id?.name || order.user_id?.name,
                internal_note: order.internal_note,
                general_customer_note: order.general_customer_note,
            },
            new: applicableChanges
                .filter((line) => line.qty > 0)
                .map((preparation_line) => preparation_line.getDataForOrderChangeReceipts()),
            cancelled: applicableChanges
                .filter((line) => line.qty < 0)
                .map((preparation_line) => preparation_line.getDataForOrderChangeReceipts()),
            noteUpdate: applicableChanges
                .filter((line) => line.qty === 0)
                .map((preparation_line) => preparation_line.getDataForOrderChangeReceipts()),
        };
    }
    async print(printer) {
        // async print() {
        // const printers = this.models["pos.printer"].getAll();
        // const results = [];

        const receiptDataObj = this.getDataForOrderChangeReceipts(printer);
        const receiptDataArray = ["new", "cancelled", "noteUpdate"]
            .filter((key) => receiptDataObj[key].length)
            .map((key) => ({
                ...receiptDataObj.baseData,
                changes: {
                    title: key,
                    data: receiptDataObj[key],
                },
            }));

        for (const receiptData of receiptDataArray) {
            const result = await printer.printReceipt(
                renderToElement("point_of_sale.OrderChangeReceipt", {
                    data: receiptData,
                })
            );

            if (!result.successful) {
                return false;
            }
        }
    }
}
// TODO: take groups into account
// async printOrderChanges(data, printer) {
//     const dataChanges = data.changes?.data;
//     if (dataChanges && dataChanges.some((c) => c.group)) {
//         const groupedData = dataChanges.reduce((acc, c) => {
//             const { name = "", index = -1 } = c.group || {};
//             if (!acc[name]) {
//                 acc[name] = { name, index, data: [] };
//             }
//             acc[name].data.push(c);
//             return acc;
//         }, {});
//         data.changes.groupedData = Object.values(groupedData).sort((a, b) => a.index - b.index);
//     }
//     const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
//         data: data,
//     });
//     return await printer.printReceipt(receipt);
// }
// filterChangeByCategories(categories, currentOrderChange) {
//     const filterFn = (change) => {
//         const product = this.models["product.product"].get(change["product_id"]);
//         const categoryIds = product.parentPosCategIds;

//         for (const categoryId of categoryIds) {
//             if (categories.includes(categoryId)) {
//                 return true;
//             }
//         }
//     };

//     return {
//         new: currentOrderChange["new"].filter(filterFn),
//         cancelled: currentOrderChange["cancelled"].filter(filterFn),
//         noteUpdate: currentOrderChange["noteUpdate"].filter(filterFn),
//     };
// }

registry.category("pos_available_models").add(PosPreparationOrder.pythonModel, PosPreparationOrder);

export class PosPreparationOrderline extends Base {
    static pythonModel = "pos.preparation.orderline";

    getDataForOrderChangeReceipts() {
        return {
            quantity: this.qty,
            display_name: this.pos_orderline_id.product_id.display_name,
            isCombo: this.pos_orderline_id.is_combo,
            attribute_value_names: this.pos_orderline_id.attribute_value_ids.map(
                (attr) => attr.name
            ),
            note: this.note,
        };
    }
}
registry
    .category("pos_available_models")
    .add(PosPreparationOrderline.pythonModel, PosPreparationOrderline);
