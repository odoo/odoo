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

export function checkPreparationTicketData(
    data,
    opts = {
        visibleInDom: [],
        invisibleInDom: [],
        lineOrder: [],
    }
) {
    const check = () => {
        const ticket = generatePreparationReceiptElement();
        const lines = ticket.querySelectorAll(".orderline");
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
                if (!ticket.innerHTML.includes(inDom)) {
                    throw new Error(`${inDom} not found in printed receipt`);
                }
            }
        }

        if (opts.invisibleInDom) {
            for (const notInDom of opts.invisibleInDom) {
                if (ticket.innerHTML.includes(notInDom)) {
                    throw new Error(`${notInDom} should not be in printed receipt`);
                }
            }
        }
    };

    return [
        {
            trigger: "body",
            run: check,
        },
    ];
}
