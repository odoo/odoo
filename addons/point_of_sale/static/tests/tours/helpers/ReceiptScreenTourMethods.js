/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickNextOrder() {
        return [
            {
                content: "go to next screen",
                trigger: ".receipt-screen .button.next.highlight",
            },
        ];
    }
    setEmail(email) {
        return [
            {
                trigger: ".receipt-screen .input-email input",
                run: `text ${email}`,
            },
        ];
    }
    clickSend(isHighlighted = true) {
        return [
            {
                trigger: `.receipt-screen .input-email .send${isHighlighted ? ".highlight" : ""}`,
            },
        ];
    }
    clickBack() {
        return [
            {
                trigger: ".receipt-screen .button.back",
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "receipt screen is shown",
                trigger: ".pos .receipt-screen",
                run: () => {},
            },
        ];
    }

    receiptIsThere() {
        return [
            {
                content: "there should be the receipt",
                trigger: ".receipt-screen .pos-receipt",
                run: () => {},
            },
        ];
    }

    totalAmountContains(value) {
        return [
            {
                trigger: `.receipt-screen .top-content h1:contains("${value}")`,
                run: () => {},
            },
        ];
    }

    emailIsSuccessful() {
        return [
            {
                trigger: `.receipt-screen .notice .successful`,
                run: () => {},
            },
        ];
    }

    customerNoteIsThere(note) {
        return [
            {
                trigger: `.receipt-screen .orderlines .pos-receipt-left-padding:contains("${note}")`,
            },
        ];
    }
}

class Execute {
    nextOrder() {
        return [...this._check.isShown(), ...this._do.clickNextOrder()];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ReceiptScreen", Do, Check, Execute));
