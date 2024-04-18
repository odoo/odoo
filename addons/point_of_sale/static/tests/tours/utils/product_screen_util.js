/** @odoo-module */

import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";

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
/**
 * Generates a sequence of actions to click on a displayed product, with optional additional
 * checks based on specific needs such as the next quantity and the next price.
 *
 * @param {string} name The name of the product to click on.
 * @param {boolean} [isCheckNeed=false] Indicates whether additional checks are necessary after clicking.
 * @param {string|null} [nextQuantity=null] The next quantity of the product, used in additional checks if specified.
 * @param {string|null} [nextPrice=null] The next price of the product, used in additional checks if specified.
 * @returns {Object[]} An array of objects describing the steps to follow
 *
 * @example
 * // Example usage for clicking on a product without additional checks.
 * clickDisplayedProduct('Gala Apple');
 *
 * // Example usage for clicking on a product with checks if the product has been added to the order.
 * clickDisplayedProduct('Gala Apple', true);
 *
 * // Example usage for clicking on a product with checks if the product has been added to the order and
 * // what should be the quantity after adding to the order.
 * clickDisplayedProduct('Gala Apple', true, "5.0");
 *
 * // Example usage for clicking on a product with checks if the product has been added to the order and
 * // what should be the quantity and price after adding to the order.
 * clickDisplayedProduct('Gala Apple', true, "5.0", "2.99");
 */
export function clickDisplayedProduct(
    name,
    isCheckNeed = false,
    nextQuantity = null,
    nextPrice = null
) {
    const step = [
        {
            content: `click product '${name}'`,
            trigger: `article.product .product-content .product-name:contains("${name}")`,
        },
    ];

    if (isCheckNeed) {
        step.push(...selectedOrderlineHas(name, nextQuantity, nextPrice));
    }

    return step;
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
/**
 * Press the numpad in sequence based on the given space-separated keys.
 * NOTE: Maximum of 2 characters because NumberBuffer only allows 2 consecutive
 * fast inputs. Fast inputs is the case in tours.
 *
 * @param {...String} keys space-separated numpad keys
 */
export function clickNumpad(...keys) {
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
export function clickRefund() {
    return [clickReview(), clickControlButtonMore(), clickControlButton("Refund")];
}
export function controlButtonTrigger(name = "") {
    return `.control-buttons button:contains("${name}")`;
}
export function clickControlButton(name) {
    return {
        content: `click ${name} button`,
        trigger: controlButtonTrigger(name),
    };
}

export function clickControlButtonMore() {
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
/**
 * Selects a given price list in the user interface. This function is designed to be used to select a specific price list.
 *
 * @param {string} name - The name of the price list to be selected. This parameter is used to identify the target element in the
 * user interface. required.
 * @param {boolean} [isCheckNeedSelectedBeforeClick=false] - A boolean that determines whether the function should check
 * if a specific item is selected before proceeding to select the price list. Useful for ensuring the user interface state
 * is correct before performing an action.
 * @param {string|null} [nameToCheck=null] - The name of the item to check if it is selected before proceeding to select the price
 * list. If this parameter is not provided (null), the `name` parameter will be used for the check.
 *
 * @example
 * // Select a price list named "Standard Rate" without prior check
 * clickPriceList("Standard Rate");
 *
 * @example
 * // Select a price list named "Discount Pricelist" after verifying that "Public Pricelist" is selected
 * clickPriceList("Discount Pricelist", true, "Public Pricelist");
 *
 * @example
 * // Select a price list named "Discount Rate" after verifying that "Discount Rate" is selected
 * clickPriceList("Discount Rate", true);
 */
export function clickPriceList(name, isCheckNeedSelectedBeforeClick = false, nameToCheck = null) {
    const step = [...clickControlButtonMore(), { trigger: ".o_pricelist_button" }];

    if (isCheckNeedSelectedBeforeClick) {
        const triggerName = nameToCheck || name;
        step.push({
            content: `verify pricelist ${triggerName} is set and selected`,
            trigger: `.selection-item.selected:contains('${triggerName}')`,
            run: function () {},
        });
    }

    step.push({
        content: `select price list '${name}'`,
        trigger: `.selection-item:contains("${name}")`,
    });

    return inLeftSide(step);
}
export function enterOpeningAmount(amount) {
    return [
        {
            content: "enter opening amount",
            trigger: ".cash-input-sub-section input",
            run: "edit " + amount,
        },
    ];
}
/**
 * Clicks on the given fiscal position in the user interface.
 *
 * @param {string} name - The name of the fiscal position to click. This parameter is used to identify the target element in the user interface.
 * @param {boolean} checkIsNeeded - A boolean indicating whether additional verification is needed after clicking on the fiscal position. If `true`, the function will verify that the fiscal position has been correctly applied to the order.
 *
 * @example
 * // Clicks on the "No Tax" fiscal position without additional verification
 * clickFiscalPosition("No Tax");
 *
 * @example
 * // Clicks on the "No Tax" fiscal position and verifies that it has been applied
 * clickFiscalPosition("No Tax", true);
 */
export function clickFiscalPosition(name, checkIsNeeded = false) {
    const step = [
        clickReview(),
        ...clickControlButtonMore(),
        {
            content: "click fiscal position button",
            trigger: ".o_fiscal_position_button",
        },
        {
            content: "fiscal position screen is shown",
            trigger: `.selection-item:contains("${name}")`,
        },
    ];

    if (checkIsNeeded) {
        step.push(
            ...clickControlButtonMore(),
            {
                content: "the fiscal position " + name + " has been set to the order",
                trigger: `.modal-body .control-buttons button.o_fiscal_position_button:contains("${name}")`,
                run: function () {},
            },
            {
                ...Dialog.cancel(),
            }
        );
    }

    step.push({
        content: "go back to the products",
        trigger: ".pos-rightheader .floor-button",
        mobile: true,
    });

    return step;
}
export function closeWithCashAmount(val) {
    return [
        {
            trigger: ".close-pos-popup .cash-input input",
            in_modal: true,
            run: `edit ${val}`,
        },
    ];
}
export function scan_barcode(barcode) {
    return [
        {
            content: `PoS model scan barcode '${barcode}'`,
            trigger: ".pos", // The element here does not really matter as long as it is present
            run: () => {
                window.posmodel.env.services.barcode_reader.scan(barcode);
            },
        },
    ];
}
export function scan_ean13_barcode(barcode) {
    return [
        {
            content: `PoS model scan EAN13 barcode '${barcode}'`,
            trigger: ".pos", // The element here does not really matter as long as it is present
            run: () => {
                const barcode_reader = window.posmodel.env.services.barcode_reader;
                barcode_reader.scan(barcode_reader.parser.sanitize_ean(barcode));
            },
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
            run: "edit " + number,
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
        ...Chrome.clickMenuOption("Close Register"),
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
            .flatMap((key) => clickNumpad(mapKey(key)));
    res.push(...selectedOrderlineHas(productName, "1.00"));
    if (unitPrice) {
        res.push(
            ...[
                clickNumpad("Price"),
                modeIsActive("Price"),
                numpadWrite(unitPrice),
                clickNumpad("Qty"),
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
            clickControlButtonMore(),
            clickControlButton("Customer Note"),
            TextInputPopup.inputText(note),
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
        ...Chrome.clickMenuOption("Close Register"),
        {
            content: "close the Point of Sale frontend",
            trigger: ".close-pos-popup .button:contains('Discard')",
            run: function () {}, //it's a check,
        },
    ];
}

export function finishOrder() {
    return [
        {
            content: "validate the order",
            trigger: ".payment-screen .button.next.highlight:visible",
            mobile: false,
        },
        {
            content: "validate the order",
            trigger: ".payment-screen .btn-switchpane:contains('Validate')",
            mobile: true,
        },
        {
            content: "verify that the order has been successfully sent to the backend",
            trigger: ".js_connected:visible",
            isCheck: true,
        },
        {
            content: "click Next Order",
            trigger: ".receipt-screen .button.next.highlight:visible",
            mobile: false,
        },
        {
            content: "Click Next Order",
            trigger: ".receipt-screen .btn-switchpane.validation-button.highlight[name='done']",
            mobile: true,
        },
        {
            content: "check if we left the receipt screen",
            trigger: ".pos-content div:not(:has(.receipt-screen))",
            run: function () {},
        },
    ];
}
