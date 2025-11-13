import { renderToElement } from "@web/core/utils/render";
import { changesToOrder } from "@point_of_sale/app/models/utils/order_change";

export function generateKioskPreparationReceipt(store) {
    const order = store.currentOrder;
    const orderData = order.getOrderData();
    const changes = changesToOrder(order, store.config.preparationCategories).new;

    const printingChanges = {
        ...orderData,
        changes: {
            title: "NEW",
            data: changes,
        },
    };

    return renderToElement("point_of_sale.OrderChangeReceipt", {
        data: printingChanges,
    });
}

export function checkKioskPreparationTicketData(
    store,
    data,
    opts = {
        visibleInDom: [],
        invisibleInDom: [],
    }
) {
    const receipt = generateKioskPreparationReceipt(store);

    const lines = receipt.querySelectorAll(".orderline");
    let idx = 0;
    for (const line of lines) {
        const name = line.firstChild.children[1].innerHTML;
        const qty = line.firstChild.children[0].innerHTML;
        const domAttrs = Object.values(line.children[1]?.children || []);
        const attrs = domAttrs.map((c) => c.innerHTML).filter(Boolean);
        const values = data[idx];

        if (values.qty != qty) {
            return `Ticket data mismatch for ${name}: expected ${values.qty}, got ${qty}`;
        }
        if (values.name != name) {
            return `Ticket data mismatch for ${name}: expected ${values.name}, got ${name}, maybe lines ordering ?`;
        }
        if (values.attributes) {
            for (const attr of values.attributes) {
                const found = attrs.find((a) => a.includes(attr));
                if (!found) {
                    return `Attribute ${attr} not found in printed receipt for ${name}`;
                }
            }
        }
        if (!values) {
            return `Received ${name} but no check data found`;
        }
        idx++;
    }
    if (opts.visibleInDom) {
        for (const inDom of opts.visibleInDom) {
            if (!receipt.innerHTML.includes(inDom)) {
                return `${inDom} not found in printed receipt`;
            }
        }
    }

    if (opts.invisibleInDom) {
        for (const notInDom of opts.invisibleInDom) {
            if (receipt.innerHTML.includes(notInDom)) {
                return `${notInDom} should not be in printed receipt`;
            }
        }
    }
    return true;
}
