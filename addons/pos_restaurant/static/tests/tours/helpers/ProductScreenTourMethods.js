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
                trigger: '.control-buttons .control-button span:contains("Internal Note")',
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
}

class CheckExt extends Check {
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
}

class ExecuteExt extends Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ProductScreen", DoExt, CheckExt, ExecuteExt));
