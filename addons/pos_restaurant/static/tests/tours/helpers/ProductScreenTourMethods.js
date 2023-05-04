/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Do, Check, Execute } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";

class DoExt extends Do {
    clickSplitBillButton() {
        return [
            {
                content: "click split bill button",
                trigger: ".control-buttons .control-button.order-split",
            },
        ];
    }
    clickTransferButton() {
        return [
            {
                content: "click transfer button",
                trigger: '.control-buttons .control-button span:contains("Transfer")',
            },
        ];
    }
    clickNoteButton() {
        return [
            {
                content: "click note button",
                trigger: '.control-buttons .control-button span:contains("Kitchen Note")',
            },
        ];
    }
    clickPrintBillButton() {
        return [
            {
                content: "click print bill button",
                trigger: ".control-buttons .control-button.order-printbill",
            },
        ];
    }
    clickSubmitButton() {
        return [
            {
                content: "click print bill button",
                trigger: '.control-buttons .control-button span:contains("Order")',
            },
        ];
    }
    clickGuestButton() {
        return [
            {
                content: "click guest button",
                trigger: '.control-buttons .control-button span:contains("Guests")',
            },
        ];
    }
    clickOrderButton() {
        return [
            {
                content: "click order button",
                trigger: ".actionpad .submit-order",
            },
        ];
    }
}

class CheckExt extends Check {
    orderlinesHaveNoChange() {
        return [
            {
                content: "Orderlines have no change",
                trigger: ".orderlines .orderline:not(.dirty)",
                run: function () {},
            },
        ];
    }
    isPrintingError() {
        // because we don't have printer in the test.
        return [
            {
                content: "Cancel printing changes",
                trigger: ".modal-dialog .cancel",
            },
        ];
    }
    orderlineIsToOrder(name) {
        return [
            {
                content: `Line is to order`,
                trigger: `.order .orderline.dirty .product-name:contains("${name}")`,
                run: function () {}, // it's a check
            },
        ];
    }
    orderlineHasNote(name, quantity, note) {
        return [
            {
                content: `line has ${quantity} quantity`,
                trigger: `.order .orderline .product-name:contains("${name}") ~ .info-list em:contains("${quantity}")`,
                run: function () {}, // it's a check
            },
            {
                content: `line has '${note}' note`,
                trigger: `.order .orderline .info-list .orderline-note:contains("${note}")`,
                run: function () {}, // it's a check
            },
        ];
    }
    guestNumberIs(numberInString) {
        return [
            {
                content: `guest number is ${numberInString}`,
                trigger: `.control-buttons .control-button span.control-button-number:contains(${numberInString})`,
                run: function () {}, // it's a check
            },
        ];
    }
    orderBtnIsPresent() {
        return [
            {
                content: "Order button is here",
                trigger: ".actionpad .button.submit-order",
                run: function () {}, // it's a check
            },
        ];
    }
}

class ExecuteExt extends Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ProductScreen", DoExt, CheckExt, ExecuteExt));
