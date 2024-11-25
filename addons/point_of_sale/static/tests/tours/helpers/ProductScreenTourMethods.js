/** @odoo-module */

import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
import * as PartnerList from "@point_of_sale/../tests/tours/helpers/PartnerListTourMethods";
import * as TextInputPopup from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as Chrome from "./ChromeTourMethods";

export function clickLine(productName, quantity = "1.0") {
    return inLeftSide([
        ...Order.hasLine({
            withoutClass: ".selected",
            run: "click",
            productName,
            quantity,
        }),
        ...Order.hasLine({ withClass: ".selected", productName, quantity }),
    ]);
}
export function clickReview() {
    return {
        content: "click review button",
        trigger: ".btn-switchpane.review-button",
        mobile: true,
    };
}
export function clickDisplayedProduct(name) {
    return [
        {
            content: `click product '${name}'`,
            trigger: `article.product .product-content .product-name:contains("${name}")`,
        },
    ];
}
export function clickInfoProduct(name) {
    return [
        {
            content: `click product '${name}'`,
            trigger: `article.product:contains("${name}") .product-information-tag`,
        },
    ];
}
export function clickOrderline(productName, quantity = "1.0") {
    return [
        ...clickLine(productName, quantity),
        {
            content: "Check the product page",
            trigger: ".product-list",
            isCheck: true,
        },
    ];
}
export function clickSubcategory(name) {
    return [
        {
            content: `selecting '${name}' subcategory`,
            trigger: `.product-screen .rightpane .category-button:contains("${name}")`,
        },
        {
            content: `'${name}' subcategory selected`,
            trigger: `button.category-button:contains("${name}")`,
            mobile: false,
            run: () => {},
        },
    ];
}
export function clickShowProductsMobile() {
    return [
        {
            content: `Click on show products in mobile mode`,
            trigger: `button.show-products-mobile`,
            mobile: true,
        },
    ];
}
/**
 * Press the numpad in sequence based on the given space-separated keys.
 * NOTE: Maximum of 2 characters because NumberBuffer only allows 2 consecutive
 * fast inputs. Fast inputs is the case in tours.
 *
 * @param {...String} keys space-separated numpad keys
 */
export function pressNumpad(...keys) {
    return inLeftSide(keys.map(Numpad.click));
}
export function clickPayButton(shouldCheck = true) {
    const steps = [
        {
            content: "click pay button",
            trigger: ".product-screen .pay-order-button",
            mobile: false,
        },
        {
            content: "click pay button",
            trigger: ".btn-switchpane:contains('Pay')",
            mobile: true,
        },
    ];
    if (shouldCheck) {
        steps.push({
            content: "now in payment screen",
            trigger: ".pos-content .payment-screen",
            run: () => {},
        });
    }
    return steps;
}
export function clickPartnerButton() {
    return [
        clickReview(),
        {
            content: "click customer button",
            trigger: ".product-screen .set-partner",
        },
        {
            content: "partner screen is shown",
            trigger: PartnerList.clickPartner().trigger,
            in_modal: true,
            run: () => {},
        },
    ];
}
export function clickCustomer(name) {
    return [PartnerList.clickPartner(name), goBackToMainScreen()];
}
export function customerIsSelected(name) {
    return [
        clickReview(),
        {
            content: `customer '${name}' is selected`,
            trigger: `.product-screen .set-partner:contains("${name}")`,
            isCheck: true,
        },
    ];
}
export function inputCustomerSearchbar(value) {
    return [
        {
            content: "click more button",
            trigger: ".modal-header .fa-search",
            mobile: true,
        },
        {
            trigger: ".modal-header .input-group input",
            run: `text ${value}`,
        },
        {
            /**
             * Manually trigger keyup event to show the search field list
             * because the previous step do not trigger keyup event.
             */
            trigger: ".modal-header .input-group input",
            run: function () {
                document
                    .querySelector(".modal-header .input-group input")
                    .dispatchEvent(new KeyboardEvent("keyup", { key: "" }));
            },
        },
    ];
}
export function clickRefund() {
    return [clickReview(), controlButtonMore(), controlButton("Refund")];
}
export function controlButtonTrigger(name = "") {
    return `.control-buttons button:contains("${name}")`;
}
export function controlButton(name) {
    return {
        content: `click ${name} button`,
        trigger: controlButtonTrigger(name),
    };
}

export function controlButtonMore() {
    return [
        {
            content: "click more button",
            trigger: ".mobile-more-button",
            mobile: true,
        },
        {
            content: "click more button",
            trigger: controlButtonTrigger("More..."),
            mobile: false,
        },
    ];
}

export function selectPriceList(name) {
    return inLeftSide([
        ...controlButtonMore(),
        { trigger: ".o_pricelist_button" },
        {
            content: `select price list '${name}'`,
            trigger: `.selection-item:contains("${name}")`,
        },
    ]);
}
export function enterOpeningAmount(amount) {
    return [
        {
            content: "enter opening amount",
            trigger: ".cash-input-sub-section input",
            run: "text " + amount,
        },
    ];
}
export function changeFiscalPosition(name) {
    return [
        clickReview(),
        ...controlButtonMore(),
        {
            content: "click fiscal position button",
            trigger: ".o_fiscal_position_button",
        },
        {
            content: "fiscal position screen is shown",
            trigger: `.selection-item:contains("${name}")`,
        },
        {
            content: "go back to the products",
            trigger: ".pos-rightheader .floor-button",
            mobile: true,
        },
    ];
}
export function closeWithCashAmount(val) {
    return [
        {
            trigger: ".close-pos-popup .cash-input input",
            in_modal: true,
            run: `text ${val}`,
        },
    ];
}
export function clickCloseSession() {
    return [
        {
            trigger: "footer .button:contains('Close Session')",
        },
    ];
}
export function goBackToMainScreen() {
    return {
        content: "go back to the products",
        trigger: ".pos-rightheader .floor-button",
        mobile: true,
    };
}
export function clickLotIcon() {
    return [
        {
            content: "click lot icon",
            trigger: ".line-lot-icon",
        },
    ];
}
export function enterLotNumber(number) {
    return [
        {
            content: "enter lot number",
            trigger: ".list-line-input:first",
            run: "text " + number,
        },
        Dialog.confirm(),
    ];
}

export function isShown() {
    return [
        {
            content: "product screen is shown",
            trigger: ".product-screen",
            run: () => {},
        },
    ];
}
export function selectedOrderlineHas(productName, quantity, price) {
    return inLeftSide(
        Order.hasLine({
            withClass: ".selected",
            productName,
            quantity,
            price,
        })
    );
}
export function orderIsEmpty() {
    return inLeftSide(Order.doesNotHaveLine());
}
export function productIsDisplayed(name) {
    return [
        {
            content: `'${name}' should be displayed`,
            trigger: `.product-list .product-name:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function totalAmountIs(amount) {
    return inLeftSide(Order.hasTotal(amount));
}
export function modeIsActive(mode) {
    return inLeftSide(Numpad.isActive(mode));
}
export function checkSecondCashClosingDetailsLineAmount(amount, sign) {
    return [
        {
            content: "Open menu",
            trigger: ".menu-button",
        },
        {
            content: "Click close session button",
            trigger: ".close-button",
        },
        {
            content: "Check closing details",
            trigger: `.cash-overview tr:nth-child(2) td:contains("${amount}")`,
            run: () => {}, // it's a check
        },
        {
            content: "Check closing details",
            trigger: `.cash-overview tr:nth-child(2) .cash-sign:contains("${sign}")`,
            run: () => {}, // it's a check
        },
    ];
}
export function noDiscountApplied(originalPrice) {
    return inLeftSide({
        content: "no discount is applied",
        trigger: `.orderline .info-list:not(:contains(${originalPrice}))`,
    });
}
export function cashDifferenceIs(val) {
    return [
        {
            trigger: `.payment-methods-overview tr td:nth-child(4):contains(${val})`,
            isCheck: true,
        },
    ];
}
// Temporarily put it here. It should be in the utility methods for the backend views.
export function lastClosingCashIs(val) {
    return [
        {
            trigger: `[name=last_session_closing_cash]:contains(${val})`,
            isCheck: true,
        },
    ];
}
export function checkFirstLotNumber(number) {
    return [
        {
            content: "Check lot number",
            trigger: `.popup-input:value(${number})`,
            run: () => {}, // it's a check
        },
    ];
}

/**
 * Create an orderline for the given `productName` and `quantity`.
 * - If `unitPrice` is provided, price of the product of the created line
 *   is changed to that value.
 * - If `expectedTotal` is provided, the created orderline (which is the currently
 *   selected orderline) is checked if it contains the correct quantity and total
 *   price.
 *
 * @param {string} productName
 * @param {string} quantity
 * @param {string} unitPrice
 * @param {string} expectedTotal
 */
export function addOrderline(productName, quantity = 1, unitPrice, expectedTotal) {
    const res = clickDisplayedProduct(productName);
    const mapKey = (key) => {
        if (key === "-") {
            return "+/-";
        }
        return key;
    };
    const numpadWrite = (val) =>
        val
            .toString()
            .split("")
            .flatMap((key) => pressNumpad(mapKey(key)));
    res.push(...selectedOrderlineHas(productName, "1.00"));
    if (unitPrice) {
        res.push(
            ...[
                pressNumpad("Price"),
                modeIsActive("Price"),
                numpadWrite(unitPrice),
                pressNumpad("Qty"),
                modeIsActive("Qty"),
            ].flat()
        );
    }
    if (quantity.toString() !== "1") {
        res.push(...numpadWrite(quantity));
    }
    res.push(...selectedOrderlineHas(productName, quantity, expectedTotal));
    return res;
}
export function addCustomerNote(note) {
    return inLeftSide(
        [
            controlButtonMore(),
            controlButton("Customer Note"),
            TextInputPopup.inputText(note),
            Dialog.confirm(),
        ].flat()
    );
}

export function addInternalNote(note) {
    return inLeftSide(
        [
            {
                content: "click more button",
                trigger: ".mobile-more-button",
                mobile: true,
            },
            controlButton("Internal Note"),
            ...(note ? [TextInputPopup.inputText(note)] : []),
            Dialog.confirm(),
        ].flat()
    );
}

export function checkOrderlinesNumber(number) {
    return [
        {
            content: `check orderlines number`,
            trigger: `.order-container .orderline`,
            run: () => {
                const orderline_amount = document.querySelectorAll(
                    ".order-container .orderline"
                ).length;
                if (orderline_amount !== number) {
                    throw new Error(`Expected ${number} orderlines, got ${orderline_amount}`);
                }
            },
        },
    ];
}

export function closePos() {
    return [
        Chrome.clickMenuButton(),
        {
            content: "open closing the Point of Sale frontend popup",
            trigger: ".close-button",
        },
        {
            content: "close the Point of Sale frontend",
            trigger: ".close-pos-popup .button:contains('Discard')",
            run: function () {}, //it's a check,
        },
    ];
}

export function checkTaxAmount(number) {
    return inLeftSide([
        {
            content: `check order tax amount`,
            trigger: `.subentry:contains("${number}")`,
        },
    ]);
}
