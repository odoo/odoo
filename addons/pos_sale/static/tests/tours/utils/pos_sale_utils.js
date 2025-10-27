import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

export function selectNthOrder(n) {
    return [
        ...ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: `select nth order`,
            trigger: `.modal:not(.o_inactive_modal) table.o_list_table tbody tr.o_data_row:nth-child(${n}) td`,
            run: "click",
        },
    ];
}

export function settleSaleOrderByPrice(price) {
    return [
        ...ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: `select sale order with price ${price}`,
            trigger: `.modal:not(.o_inactive_modal) table.o_list_table tbody tr.o_data_row td:contains('${price}')`,
            run: "click",
        },
        {
            content: `Choose to settle the order`,
            trigger: `.modal:not(.o_inactive_modal) .selection-item:contains('Settle the order')`,
            run: "click",
        },
    ];
}

export function settleNthOrder(n, options = {}) {
    const { loadSN } = options;
    const step = [
        ...selectNthOrder(n),
        {
            content: `Choose to settle the order`,
            trigger: `.modal:not(.o_inactive_modal) .selection-item:contains('Settle the order')`,
            run: "click",
        },
    ];
    if (loadSN !== undefined) {
        step.push({
            content: `Choose to auto link the lot number to the order line`,
            trigger: `.modal-content:contains('Do you want to load the SN/Lots linked to the Sales Order?') button:contains('${
                loadSN ? "Ok" : "Cancel"
            }')`,
            run: "click",
        });
    }
    step.push({
        trigger: "body:not(:has(.modal))",
    });
    return step;
}

export function downPaymentFirstOrder(amount) {
    return [
        ...selectNthOrder(1),
        {
            content: `click on select the order`,
            trigger: `.selection-item:contains('Apply a down payment')`,
            run: "click",
        },
        Numpad.click(amount),
        Dialog.confirm("Ok"),
    ];
}

export function checkOrdersListEmpty() {
    return [
        ...ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: "Check that the orders list is empty",
            trigger: "p:contains(No record found)",
        },
    ];
}

export function selectedOrderLinesHasLots(productName, lots) {
    const getSerialStep = (index, serialNumber) => ({
        content: `check lot${index} is linked`,
        trigger: `.info-list li:contains(${serialNumber})`,
    });
    const lotSteps = lots.reduce((acc, serial, i) => acc.concat(getSerialStep(i, serial)), []);
    return [...ProductScreen.selectedOrderlineHas(productName), ...lotSteps];
}

export function checkOrdersListNotEmpty() {
    return [
        ...ProductScreen.clickControlButton("Quotation/Order"),
        {
            content: "Check that the orders list is not empty",
            trigger: ".o_data_row",
        },
    ];
}
