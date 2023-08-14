/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Do, Check, Execute } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

class DoExt extends Do {
    clickSplitBillButton() {
        return [
            {
                content: "click split bill button",
                trigger: ".control-buttons .control-button.order-split",
            },
        ];
    }
    doubleClickOrderline(name) {
        return Order.hasLine({ productName: name, run: "dblclick" });
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
            {
                content: "Close printing error",
                trigger: ".popup-error .cancel",
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
        return Order.doesNotHaveLine({ withClass: ".has-change" });
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
        return Order.hasLine({
            productName: name,
            withClass: ".has-change.text-success.border-start.border-success.border-4",
        });
    }
    orderlineIsToSkip(name) {
        return Order.hasLine({
            withClass: ".skip-change.text-primary.border-start.border-primary.border-4",
            productName: name,
        });
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
