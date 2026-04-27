/* @odoo-module */

export const stepUtils = {
    confirmAddingUnreservedProduct() {
        return [
            {
                trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Add extra product?)",
            },
            {
                trigger: ".modal:not(.o_inactive_modal) .btn-primary",
                run: "click",
            },
            {
                trigger: "body:not(:has(.modal))",
            },
        ];
    },
    inputManuallyBarcode(barcode) {
        return [
            { trigger: '.o_barcode_actions', run: "click" },
            { trigger: 'input#manual_barcode', run: "click" },
            { trigger: 'input#manual_barcode', run: `edit ${barcode}` },
            { trigger: 'input#manual_barcode+button', run: "click" },
        ];
    },
    validateBarcodeOperation(trigger = ".o_barcode_client_action .o_barcode_lines") {
        return [
            {
                trigger: "body:not(:has(.modal))",
            },
            {
                trigger,
                run: "scan OBTVALI",
            },
            {
                trigger: ".o_notification_bar.bg-success",
            },
        ];
    },
    discardBarcodeForm() {
        return [
            {
                isActive: ["auto"],
                content: "discard barcode form",
                trigger: ".o_discard",
                run: "click",
            },
            {
                content: "wait to be back on the barcode lines",
                trigger: ".o_add_line",
            },
        ];
    },
    // RFID utils.
    countUniqRFID(count) {
        return [{ trigger: `.o_barcode_count_rfid .o_rfid_unique_tags:contains(${count})` }];
    },
    countTotalRFID(count) {
        return [{ trigger: `.o_barcode_count_rfid .o_rfid_total_read:contains(${count})` }];
    },
    closeCountRFID() {
        return [{ trigger: ".o_barcode_count_rfid button.btn-close" }];
    },
    decrementLotLineQty(lineName) {
        return [
            {
                trigger: `.o_barcode_line_details .o_line_lot_name:contains(${lineName})`,
                run: "click",
            },
            {
                trigger: `.o_barcode_line:contains(${lineName}) .o_remove_unit`,
                run: "click",
            },
        ];
    },
};
