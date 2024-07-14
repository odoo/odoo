/* @odoo-module */

export const stepUtils = {
    confirmAddingUnreservedProduct() {
        return {
            trigger: '.btn-primary',
            extra_trigger: '.modal-title:contains("Add extra product?")',
            in_modal: true,
        };
    },
    validateBarcodeOperation(trigger = '.o_barcode_client_action') {
        return [
            {
                trigger,
                run: 'scan O-BTN.validate',
            },
            {
                trigger: '.o_notification.border-success',
                isCheck: true,
            },
        ];
    },
    discardBarcodeForm() {
        return [
            {
                content: 'discard barcode form',
                trigger: '.o_discard',
                auto: true,
            },
            {
                content: 'wait to be back on the barcode lines',
                trigger: '.o_add_line',
                auto: true,
                run() {},
            },
        ];
    },
};
