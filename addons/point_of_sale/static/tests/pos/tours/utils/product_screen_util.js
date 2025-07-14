import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { back as utilsBack, inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { LONG_PRESS_DURATION } from "@point_of_sale/utils";

export function firstProductIsFavorite(name) {
    return [
        {
            content: `first product is '${name}'`,
            trigger: `.product-list .product:first-of-type .product-name:contains("${name}")`,
        },
    ];
}

export function clickLine(productName, quantity = "1") {
    return [
        ...Order.hasLine({
            withoutClass: ".selected",
            run: "click",
            productName,
            quantity,
        }),
        ...Order.hasLine({ withClass: ".selected", productName, quantity }),
    ].flat();
}
export function clickSelectedLine(productName, quantity = "1") {
    return [
        ...Order.hasLine({
            withClass: ".selected",
            run: "click",
            productName,
            quantity,
        }),
        ...Order.hasLine({ withoutClass: ".selected", productName, quantity }),
    ].flat();
}
export function clickReview() {
    return {
        isActive: ["mobile"],
        content: "click review button",
        trigger: ".btn-switchpane.review-button",
        run: "click",
    };
}
export function selectFloatingOrder(index) {
    return [
        {
            isActive: ["mobile"],
            trigger: ".fa-caret-down",
            run: "click",
        },
        {
            trigger: `.list-container-items .btn:eq(${index})`,
            run: "click",
        },
    ];
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
            run: "click",
        },
    ];

    if (isCheckNeed) {
        step.push(...selectedOrderlineHas(name, nextQuantity, nextPrice));
    }
    if (isCheckNeed && nextQuantity) {
        step.push(...productCardQtyIs(name, nextQuantity));
    }

    return step;
}
export function clickInfoProduct(name, extraSteps = []) {
    return [
        ...clickDisplayedProduct(name),
        ...inLeftSide([...clickControlButton("Info"), ...extraSteps]),
    ];
}
export function clickOrderline(productName, quantity = "1") {
    return [
        ...clickLine(productName, quantity),
        {
            content: "Check the product page",
            trigger: ".product-list",
        },
    ];
}
export function clickSubcategory(name) {
    return [
        {
            content: `selecting '${name}' subcategory`,
            trigger: `.product-screen .rightpane .category-button:contains("${name}")`,
            run: "click",
        },
        {
            isActive: ["desktop"],
            content: `'${name}' subcategory selected`,
            trigger: `button.category-button:contains("${name}")`,
        },
    ];
}
/**
 * Press the numpad in sequence based on the given space-separated keys.
 * @param {...String} keys space-separated numpad keys
 */
export function clickNumpad(...keys) {
    return inLeftSide(keys.map(Numpad.click));
}
export function clickPayButton(shouldCheck = true) {
    const steps = [
        {
            isActive: ["desktop"],
            content: "click pay button",
            trigger: ".product-screen .pay-order-button",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "click pay button",
            trigger: ".btn-switchpane:contains('Pay')",
            run: "click",
        },
    ];
    if (shouldCheck) {
        steps.push({
            content: "now in payment screen",
            trigger: ".pos-content .payment-screen",
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
            run: "click",
        },
        {
            content: "partner screen is shown",
            trigger: `${PartnerList.clickPartner().trigger}`,
        },
    ];
}
export function clickCustomer(name) {
    return [PartnerList.clickPartner(name), { ...back(), isActive: ["mobile"] }];
}
export function selectPreset(selectedPreset, presetToSelect) {
    return [
        clickReview(),
        {
            content: "click preset button",
            trigger: `.product-screen button:contains("${selectedPreset}")`,
            run: "click",
        },
        {
            content: `click preset '${presetToSelect}' from preset modal`,
            trigger: `.modal-body button:contains(${presetToSelect})`,
            run: "click",
        },
    ];
}
export function customerIsSelected(name) {
    return [
        clickReview(),
        {
            content: `customer '${name}' is selected`,
            trigger: `.product-screen .set-partner:contains("${name}")`,
        },
    ];
}
export function clickRefund() {
    return [clickReview(), ...clickControlButton("Refund")];
}
export function controlButtonTrigger(name = "") {
    return `.control-buttons button:contains("${name}")`;
}
export function clickControlButton(name) {
    return [
        ...clickControlButtonMore(),
        {
            content: `click ${name} button`,
            trigger: controlButtonTrigger(name),
            run: "click",
        },
    ];
}
export function clickCloseButton() {
    return [
        {
            trigger: `.btn-close`,
            run: "click",
        },
    ];
}
export function clickControlButtonMore() {
    return [
        {
            isActive: ["mobile"],
            content: "click Actions button",
            trigger: ".mobile-more-button",
            run: "click",
        },
        {
            isActive: ["desktop"],
            content: "click Actions button",
            trigger: ".more-btn",
            run: "click",
        },
    ];
}

export function clickInternalNoteButton(buttonLabel) {
    return [
        {
            isActive: ["mobile"],
            content: "click Actions button",
            trigger: ".mobile-more-button",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "click Internal note button",
            trigger: `.modal-body button:contains("${buttonLabel}")`,
            run: "click",
        },
        {
            isActive: ["desktop"],
            content: "click Internal Note button",
            trigger: controlButtonTrigger(buttonLabel),
            run: "click",
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
    const step = [
        ...clickControlButtonMore(),
        {
            trigger: ".o_pricelist_button",
            run: "click",
        },
    ];

    if (isCheckNeedSelectedBeforeClick) {
        const triggerName = nameToCheck || name;
        step.push({
            content: `verify pricelist ${triggerName} is set and selected`,
            trigger: `.selection-item.selected:contains('${triggerName}')`,
        });
    }

    step.push({
        content: `select price list '${name}'`,
        trigger: `.selection-item:contains("${name}")`,
        run: "click",
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
            run: "click",
        },
        {
            content: "fiscal position screen is shown",
            trigger: `.selection-item:contains("${name}")`,
            run: "click",
        },
    ];

    if (checkIsNeeded) {
        step.push(
            ...clickControlButtonMore(),
            {
                content: "the fiscal position " + name + " has been set to the order",
                trigger: `.o_fiscal_position_button:contains("${name}")`,
            },
            {
                content: "cancel dialog",
                trigger: ".modal .modal-header button[aria-label='Close']",
                run: "click",
            }
        );
    }

    return [...step, { ...back(), isActive: ["mobile"] }];
}
export function checkFiscalPosition(name) {
    return [
        clickReview(),
        ...clickControlButtonMore(),
        {
            content: `check fiscal position '${name}' is selected`,
            trigger: `.o_fiscal_position_button:contains("${name}")`,
            run: () => {},
        },
        Dialog.cancel(),
    ];
}
export function closeWithCashAmount(val) {
    return [
        {
            trigger: ".modal .close-pos-popup .cash-input input",
            run: `edit ${val}`,
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
export function back() {
    return utilsBack();
}
export function clickLotIcon() {
    return [
        {
            content: "click lot icon",
            trigger: ".line-lot-icon",
            run: "click",
        },
    ];
}
export function deleteNthLotNumber(number) {
    return [
        {
            content: "delete lot number",
            trigger: `.lot-container .lot-item:eq(${number - 1}) .btn`,
            run: "click",
        },
    ];
}
export function selectNthLotNumber(number) {
    return [
        {
            trigger: `.o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item:eq(${
                number - 1
            })`,
            run: "click",
        },
        Dialog.confirm(),
    ];
}
export function enterLotNumber(number, tracking = "serial", click = false) {
    const steps = [];
    if (click) {
        steps.push({
            trigger: ".o-autocomplete input",
            run: "click",
        });
    }
    steps.push(
        {
            trigger:
                ".o-autocomplete--dropdown-item a:contains('No existing Lot/Serial number found...')",
        },
        {
            content: "enter lot number",
            trigger: ".o-autocomplete input",
            run: "edit " + number,
        },
        {
            trigger: ".o-autocomplete--dropdown-item a:contains('Create Lot/Serial number...')",
        },
        {
            trigger: ".o-autocomplete input",
            run: "press Enter",
        }
    );
    if (tracking === "serial") {
        steps.push(...serialCheckStep(number));
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function serialCheckStep(number) {
    return [
        {
            content: "Check entered lot/serial number",
            trigger: `.lot-container .lot-item:eq(-1) span:contains(${number})`,
        },
        {
            trigger: ".o-autocomplete input:value()",
        },
    ];
}

export function enterExistingLotNumber(number, tracking = "serial") {
    const steps = [];
    steps.push(
        {
            content: "enter lot number",
            trigger: ".o-autocomplete input",
            run: "edit " + number,
        },
        {
            trigger: ".o-autocomplete input",
            run: "press Enter",
        }
    );
    if (tracking === "serial") {
        steps.push(...serialCheckStep(number));
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function enterLotNumbers(numbers) {
    const steps = [
        {
            trigger: ".o-autocomplete input",
            run: "click",
        },
    ];
    for (const lot of numbers) {
        steps.push(
            {
                content: "enter lot number",
                trigger: ".o-autocomplete input",
                run: "edit " + lot,
            },
            {
                trigger: ".o-autocomplete--dropdown-item a:contains('Create Lot/Serial number...')",
            },
            {
                trigger: ".o-autocomplete input",
                run: "press Enter",
            },
            {
                content: "check entered lot number",
                trigger: `.lot-container .lot-item:eq(-1) span:contains(${lot})`,
            },
            {
                trigger: ".o-autocomplete input:value()",
            }
        );
    }
    steps.push(Dialog.confirm());
    return steps;
}

export function isShown() {
    return [
        {
            content: "product screen is shown",
            trigger: ".product-screen",
        },
    ];
}
export function selectedOrderlineHas(productName, quantity, price, attributeLine = "") {
    return inLeftSide(
        Order.hasLine({
            withClass: ".selected",
            productName,
            quantity,
            price,
            attributeLine,
        })
    );
}
export function selectedOrderlineHasDirect(productName, quantity, price) {
    return Order.hasLine({
        withClass: ".selected",
        productName,
        quantity,
        price,
    });
}
export function orderComboLineHas(productName, quantity) {
    return Order.hasLine({
        productName,
        quantity,
    });
}
export function orderLineHas(productName, quantity, price) {
    return Order.hasLine({
        productName,
        quantity,
        price,
    });
}
export function orderIsEmpty() {
    return inLeftSide(Order.doesNotHaveLine());
}

/**
 * @param {number} position The position of the product in the list. If -1 (default), the product can be anywhere in the list.
 */
export function productIsDisplayed(name, position = -1) {
    return [
        {
            content: `'${name}' should be displayed`,
            trigger: `.product-list ${
                position > -1 ? `article:eq(${position})` : ""
            } .product-name:contains("${name}")`,
        },
    ];
}
export function searchProduct(string) {
    return [
        {
            isActive: ["mobile"],
            content: `Click search field`,
            trigger: `.fa-search`,
            run: `click`,
        },
        {
            content: "Search for a product using the search bar",
            trigger: ".pos-rightheader .form-control > input",
            run: `edit ${string}`,
        },
    ];
}
export function totalAmountIs(amount) {
    return inLeftSide(...Order.hasTotal(amount));
}
export function modeIsActive(mode) {
    return inLeftSide(Numpad.isActive(mode));
}
export function cashDifferenceIs(val) {
    return [
        {
            trigger: `.payment-methods-overview .cash-difference:contains(${val})`,
        },
    ];
}
export function productCardQtyIs(productName, qty) {
    qty = `${Number.parseFloat(Number.parseFloat(qty).toFixed(2))}`;
    return [
        {
            content: `'${productName}' should have '${qty}' quantity`,
            trigger: `article.product .product-content:has(.product-name:contains("${productName}")):has(.product-cart-qty:contains("${qty}"))`,
        },
    ];
}

// Temporarily put it here. It should be in the utility methods for the backend views.
export function lastClosingCashIs(val) {
    return [
        {
            trigger: `[name=last_session_closing_cash]:contains(${val})`,
        },
    ];
}
export function checkFirstLotNumber(number) {
    return [
        {
            content: "Check lot number",
            trigger: `.lot-container .lot-item:eq(0) span:contains(${number})`,
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
    const initialStep = clickDisplayedProduct(productName);
    const res = [];
    const mapKey = (key) => {
        if (key === "-") {
            return "+/-";
        }
        return key;
    };

    // Press +/- to set a negative quantity. For example, pressing +/- followed by "1" will result in "-11".
    // To adjust the quantity from "-1" to "-3," first press "0" followed by "3" since pressing +/- will initially set it to "-1,"
    // and entering "3" directly would result in "-13." so send 0(num) when want to change sign and set a number
    const numpadWrite = (val) =>
        val
            .toString()
            .split("")
            .flatMap((key) => Numpad.click(mapKey(key)));
    res.push(...selectedOrderlineHasDirect(productName, "1"));
    if (unitPrice) {
        res.push(
            ...[
                Numpad.click("Price"),
                Numpad.isActive("Price"),
                numpadWrite(unitPrice),
                Numpad.click("Qty"),
                Numpad.isActive("Qty"),
            ].flat()
        );
    }
    if (quantity.toString() !== "1") {
        res.push(...numpadWrite(quantity));
    }
    res.push(...selectedOrderlineHasDirect(productName, quantity, expectedTotal));
    return [initialStep, inLeftSide(res)].flat();
}
export function addCustomerNote(note) {
    return [
        clickControlButton("Customer Note"),
        TextInputPopup.inputText(note),
        Dialog.confirm(),
    ].flat();
}
export function addInternalNote(note, buttonLabel = "Note") {
    return [
        clickInternalNoteButton(buttonLabel),
        TextInputPopup.inputText(note),
        Dialog.confirm(),
    ].flat();
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
        },
    ];
}

export function finishOrder() {
    return [
        {
            isActive: ["desktop"],
            content: "validate the order",
            trigger: ".payment-screen .button.next.highlight:visible",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "validate the order",
            trigger: ".payment-screen .btn-switchpane:contains('Validate')",
            run: "click",
        },
        Chrome.isSyncStatusConnected(),
        {
            isActive: ["desktop"],
            content: "click Next Order",
            trigger: ".receipt-screen .button.next.highlight:visible",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "Click Next Order",
            trigger: ".receipt-screen .btn-switchpane.validation-button.highlight[name='done']",
            run: "click",
        },
        {
            content: "check if we left the receipt screen",
            trigger: ".pos-content div:not(:has(.receipt-screen))",
        },
    ];
}

export function checkTaxAmount(amount) {
    return {
        trigger: `.order-summary .tax:contains(${amount})`,
    };
}

export function checkRoundingAmountIsNotThere() {
    return [
        {
            isActive: ["desktop"], // not rendered on mobile
            trigger: ".order-summary",
            run: function () {
                if (document.querySelector(".rounding")) {
                    throw new Error("A rounding amount has been found in order display.");
                }
            },
        },
    ];
}

export function checkRoundingAmount(amount) {
    return {
        trigger: `.order-summary .rounding:contains(${amount})`,
    };
}

export function customerIs(name) {
    return [
        {
            trigger: `.product-screen .set-partner:contains("${name}")`,
        },
    ];
}

export function checkTotalAmount(amount) {
    return {
        trigger: `.order-summary .total:contains(${amount})`,
    };
}

export function selectCategoryAndAddProduct(categoryName, productName) {
    return [
        {
            trigger: `.category-button > span:contains(${categoryName})`,
            run: "click",
        },
        ...addOrderline(productName, "1"),
    ];
}

export function verifyCategorySequence(categories) {
    return categories.map((category, index) => ({
        content: `Verify '${category}' category has sequence number ${index + 1}`,
        trigger: `.category-button > span:contains("${category}")`,
    }));
}

export function verifyOrderlineSequence(products) {
    return products.map((productName, index) => ({
        content: `Verify orderline for '${productName}' is at seq ${index + 1}`,
        trigger: `.order-container .orderline:nth-child(${
            index + 1
        }) span:contains("${productName}")`,
    }));
}

export function checkProductExtraPrice(productName, extraAmount) {
    return {
        content: `'${productName}' should have '${extraAmount}' extra price`,
        trigger: `article.product:has(.product-name:contains("${productName}")):has(.price-extra:contains("${extraAmount}"))`,
    };
}

export function addDiscount(discount) {
    return [
        Numpad.click("%"),
        Numpad.isActive("%"),
        discount
            .toString()
            .split("")
            .flatMap((key) => Numpad.click(key)),
    ].flat();
}

export function setTimeZone(testTimeZone) {
    return {
        content: `Set test time zone to ${testTimeZone}`,
        trigger: "body",
        run: function () {
            luxon.Settings.defaultZone = testTimeZone;
        },
    };
}

function productInputSteps(name, barcode, list_price) {
    return [
        {
            content: "Enter product name.",
            trigger: 'div[name="name"] input',
            run: `edit ${name}`,
        },
        {
            content: "Enter barcode to fetch product data using barcodelookup.",
            trigger: 'div[name="barcode"] input',
            run: `edit ${barcode}`,
        },
        {
            content: "Enter list_price.",
            trigger: 'div[name="list_price"] input',
            run: `edit ${list_price}`,
        },
    ];
}

export function createProductFromFrontend(name, barcode, list_price, category) {
    return [
        ...productInputSteps(name, barcode, list_price),
        {
            isActive: ["desktop"],
            content: "Remove default tax 15%.",
            trigger: 'div[name="taxes_id"] .o_delete:not(:visible)',
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "Remove default tax 15%.",
            trigger: 'div[name="taxes_id"] .o_delete',
            run: "click",
        },
        {
            content: "Open category selector.",
            trigger: 'div[name="pos_categ_ids"] input',
            run: "click",
        },
        {
            isActive: ["desktop"],
            content: "Select category.",
            trigger: `.o_input_dropdown .o-autocomplete--dropdown-menu li:contains(${category})`,
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "Select category.",
            trigger: `.o_kanban_renderer .o_kanban_record span:contains(${category})`,
            run: "click",
        },
    ];
}

export function editProductFromFrontend(name, barcode, list_price) {
    return productInputSteps(name, barcode, list_price);
}

export function longPressProduct(productName) {
    return [
        {
            content: `Long pressing product "${productName}"...`,
            trigger: `.product-name:contains("${productName}")`,
            run: async () => {
                const el = document.querySelector(".product-name");
                const mouseDown = new MouseEvent("mousedown", { bubbles: true });
                const mouseUp = new MouseEvent("mouseup", { bubbles: true });
                el.dispatchEvent(mouseDown);
                await new Promise((resolve) => setTimeout(resolve, LONG_PRESS_DURATION + 50));
                el.dispatchEvent(mouseUp);
            },
        },
    ];
}

export function isEmpty() {
    return {
        content: "Verify that the Product Screen is empty",
        trigger: ".product-screen:not(:has(.product-list))",
    };
}

export function loadSampleButtonIsThere() {
    return {
        content: "Click Load Sample",
        trigger: ".product-screen .o_nocontent_help button:contains('Load Sample')",
    };
}
