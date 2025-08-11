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

export function checkPreparationTicketData(
    data,
    opts = {
        visibleInDom: [],
        invisibleInDom: [],
        lineOrder: [],
        fireCourse: false,
    }
) {
    const check = async () => {
        let tickets = [];

        if (opts.fireCourse) {
            tickets = await generateFireCourseReceipts();
        } else {
            tickets = await generatePreparationReceipts();
        }

        if (
            !tickets[0] &&
            !data.length &&
            !opts.invisibleInDom?.length &&
            !opts.visibleInDom?.length &&
            !opts.lineOrder?.length &&
            !opts.fireCourse
        ) {
            return true;
        }

        const lines = tickets[0].querySelectorAll(".orderline");
        const lineNames = [];

        let idx = 0;
        for (const line of lines) {
            const name = line.firstChild.children[1].innerHTML;
            const qty = line.firstChild.children[0].innerHTML;
            const domAttrs = Object.values(line.children[1]?.children || []);
            const attrs = domAttrs.map((c) => c.innerHTML).filter(Boolean);
            const values = data[idx];

            if (values.qty != qty) {
                throw new Error(
                    `Ticket data mismatch for ${name}: expected ${values.qty}, got ${qty}`
                );
            }

            if (values.name != name) {
                throw new Error(
                    `Ticket data mismatch for ${name}: expected ${values.name}, got ${name}, maybe lines ordering ?`
                );
            }

            if (values.attributes) {
                for (const attr of values.attributes) {
                    const found = attrs.find((a) => a.includes(attr));
                    if (!found) {
                        throw new Error(
                            `Attribute ${attr} not found in printed receipt for ${name}`
                        );
                    }
                }
            }

            if (!values) {
                throw new Error(`Received ${name} but no check data found`);
            }

            lineNames.push(name);
            idx++;
        }

        if (opts.visibleInDom) {
            for (const inDom of opts.visibleInDom) {
                let found = false;
                for (const ticket of tickets) {
                    if (ticket.innerHTML.includes(inDom)) {
                        found = true;
                    }
                }
                if (!found) {
                    throw new Error(`${inDom} not found in printed receipt`);
                }
            }
        }

        if (opts.invisibleInDom) {
            for (const notInDom of opts.invisibleInDom) {
                for (const ticket of tickets) {
                    if (ticket.innerHTML.includes(notInDom)) {
                        throw new Error(`${notInDom} should not be in printed receipt`);
                    }
                }
            }
        }
    };

    return [
        {
            trigger: "body",
            run: async () => await check(),
        },
    ];
}
