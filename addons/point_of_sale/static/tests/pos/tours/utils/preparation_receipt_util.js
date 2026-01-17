/* global posmodel */

import { _t } from "@web/core/l10n/translation";

async function generateReceiptsToPrint(order, opts = {}) {
    const models = posmodel.models;
    const generator = posmodel.ticketPrinter.getGenerator({ models, order });
    const categories = posmodel.config.printerCategories;
    const changes = generator.generatePreparationData(new Set(categories), opts);
    const template = "point_of_sale.pos_order_change_receipt";
    const tickets = [];

    for (const change of changes) {
        const iframe = await posmodel.ticketPrinter.generateIframe(template, change);
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        tickets.push(doc.getElementById("pos-receipt"));
    }

    return tickets;
}

// Return rendered fire course receipts that will be printed when clicking "Fire course" button
async function generateFireCourseReceipts() {
    const order = posmodel.getOrder();
    const course = order.getSelectedCourse();
    const orderChange = {
        new: [],
        cancelled: [],
        noteUpdate: course.lines.map((line) => ({ product_id: line.getProduct().id })),
        noteUpdateTitle: `${course.name} ${_t("fired")}`,
        printNoteUpdateData: false,
    };
    return await generateReceiptsToPrint(order, { orderChange });
}

// Return rendered order change receipts that will be printed when clicking "Order" button
export async function generatePreparationReceipts() {
    return await generateReceiptsToPrint(posmodel.getOrder());
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
            !tickets.length &&
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
            const values = data[idx];
            if (!values) {
                idx++;
                continue;
            }

            const name = line.firstChild.children[1].innerHTML;
            const qty = line.firstChild.children[0].innerHTML;
            const domAttrs = Object.values(line.children[1]?.children || []);
            const attrs = domAttrs.map((c) => c.innerHTML).filter(Boolean);

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
