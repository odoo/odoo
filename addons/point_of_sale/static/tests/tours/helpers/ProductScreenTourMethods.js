/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { TextAreaPopup } from "@point_of_sale/../tests/tours/helpers/TextAreaPopupTourMethods";
import { Numpad } from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

export function adaptForMobile(steps) {
    return [
        {
            content: "click review button",
            trigger: ".btn-switchpane:contains('Review')",
            mobile: true,
        },
        ...[steps].flat(),
        {
            content: "go back to the products",
            trigger: ".pos-rightheader .floor-button",
            mobile: true,
        },
    ];
}

export function clickLine(productName, quantity = "1.0") {
    return adaptForMobile([
        ...Order.hasLine({
            withoutClass: ".selected",
            run: "click",
            productName,
            quantity,
        }),
        ...Order.hasLine({ withClass: ".selected", productName, quantity }),
    ]);
}
class Do {
    clickDisplayedProduct(name) {
        return [
            {
                content: `click product '${name}'`,
                trigger: `article.product .product-content .product-name:contains("${name}")`,
            },
        ];
    }

    clickOrderline(productName, quantity = "1.0") {
        return [
            ...clickLine(productName, quantity),
            {
                content: "Check the product page",
                trigger: ".product-list-container .product-list",
                isCheck: true,
            },
        ];
    }

    clickSubcategory(name) {
        return [
            {
                content: `selecting '${name}' subcategory`,
                trigger: `.products-widget > .products-widget-control .category-button:contains("${name}")`,
            },
            {
                content: `'${name}' subcategory selected`,
                trigger: `i.fa-caret-right ~ button.category-button:contains("${name}")`,
                run: () => {},
            },
        ];
    }

    clickHomeCategory() {
        return [
            {
                content: `click Home subcategory`,
                trigger: `button.category-button i.fa-home`,
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
    pressNumpad(...keys) {
        return adaptForMobile(keys.map(Numpad.click));
    }

    clickPayButton(shouldCheck = true) {
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

    clickPartnerButton() {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                content: "click customer button",
                trigger: ".product-screen .set-partner",
            },
            {
                content: "partner screen is shown",
                trigger: ".pos-content .partnerlist-screen",
                run: () => {},
            },
        ];
    }

    clickCustomer(name) {
        return [
            {
                content: `select customer '${name}'`,
                trigger: `.partnerlist-screen .partner-line td:contains("${name}")`,
            },
            {
                content: "go back to the products",
                trigger: ".pos-rightheader .floor-button",
                mobile: true,
            },
        ];
    }

    clickOrderlineCustomerNoteButton() {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                content: "click more button",
                trigger: ".mobile-more-button",
                mobile: true,
            },
            {
                content: "click customer note button",
                trigger: '.control-buttons .control-button span:contains("Customer Note")',
            },
        ];
    }
    clickRefund() {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                content: "click more button",
                trigger: ".mobile-more-button",
                mobile: true,
            },
            {
                trigger: '.control-button:contains("Refund")',
            },
        ];
    }
    confirmOpeningPopup() {
        return [{ trigger: '.opening-cash-control .button:contains("Open session")' }];
    }
    selectPriceList(name) {
        return adaptForMobile([
            {
                content: "click more button",
                trigger: ".mobile-more-button",
                mobile: true,
            },
            { trigger: ".o_pricelist_button" },
            {
                content: `select price list '${name}'`,
                trigger: `.selection-item:contains("${name}")`,
            },
        ]);
    }
    enterOpeningAmount(amount) {
        return [
            {
                content: "enter opening amount",
                trigger: ".cash-input-sub-section input",
                run: "text " + amount,
            },
        ];
    }
    changeFiscalPosition(name) {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                content: "click more button",
                trigger: ".mobile-more-button",
                mobile: true,
            },
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
    clickCloseButton() {
        return [
            {
                trigger: ".close-button",
            },
        ];
    }
    closeWithCashAmount(val) {
        return [
            {
                trigger: "div.popup.close-pos-popup input",
                run: `text ${val}`,
            },
        ];
    }
    clickCloseSession() {
        return [
            {
                trigger: "footer .button:contains('Close Session')",
            },
        ];
    }
    scan_barcode(barcode) {
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
    scan_ean13_barcode(barcode) {
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
    goBackToMainScreen() {
        return [
            {
                content: "go back to the products",
                trigger: ".pos-rightheader .floor-button",
                mobile: true,
            },
        ];
    }
    clickLotIcon() {
        return [
            {
                content: 'click lot icon',
                trigger: '.line-lot-icon',
            },
        ];
    }
    enterLotNumber(number) {
        return [
            {
                content: 'enter lot number',
                trigger: '.list-line-input:first()',
                run: 'text ' + number,
            },
            {
                content: 'click validate lot number',
                trigger: '.popup .button.confirm',
            }
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "product screen is shown",
                trigger: ".product-screen",
                run: () => {},
            },
        ];
    }
    selectedOrderlineHas(name, quantity, price, comboParent) {
        return [
            ...adaptForMobile(
                Order.hasLine({
                    withClass: ".selected",
                    productName: name,
                    quantity,
                    price,
                    comboParent,
                })
            ),
            {
                content: "Check the product page",
                trigger: ".product-list-container .product-list",
                isCheck: true,
            },
        ];
    }
    orderIsEmpty() {
        return adaptForMobile(Order.doesNotHaveLine());
    }

    productIsDisplayed(name) {
        return [
            {
                content: `'${name}' should be displayed`,
                trigger: `.product-list .product-name:contains("${name}")`,
                run: () => {},
            },
        ];
    }
    totalAmountIs(amount) {
        return [
            ...adaptForMobile(Order.hasTotal(amount)),
            {
                content: "Check the product page",
                trigger: ".product-list-container .product-list",
                isCheck: true,
            },
        ];
    }
    totalTaxIs(amount) {
        return adaptForMobile(Order.hasTax(amount));
    }
    modeIsActive(mode) {
        return adaptForMobile(Numpad.isActive(mode));
    }
    checkSecondCashClosingDetailsLineAmount(amount, sign) {
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
    noDiscountApplied(originalPrice) {
        return adaptForMobile({
            content: "no discount is applied",
            trigger: `.orderline .info-list:not(:contains(${originalPrice}))`,
        });
    }
    discountOriginalPriceIs(original_price) {
        return [
            {
                content: "click review button",
                trigger: ".btn-switchpane:contains('Review')",
                mobile: true,
            },
            {
                content: `discount original price is shown`,
                trigger: `s:contains('${original_price}')`,
                run: function () {},
            },
            {
                content: "go back to the products",
                trigger: ".pos-rightheader .floor-button",
                mobile: true,
            },
        ];
    }
    cashDifferenceIs(val) {
        return [
            {
                trigger: `.payment-methods-overview tr td:nth-child(4):contains(${val})`,
                isCheck: true,
            },
        ];
    }
    // Temporarily put it here. It should be in the utility methods for the backend views.
    lastClosingCashIs(val) {
        return [
            {
                trigger: `[name=last_session_closing_cash]:contains(${val})`,
                isCheck: true,
            },
        ];
    }
    checkFirstLotNumber(number) {
        return [
            {
                content: 'Check lot number',
                trigger: `.popup-input:propValue(${number})`,
                run: () => {}, // it's a check
            },
        ];
    }
}

class Execute {
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
    addOrderline(productName, quantity = 1, unitPrice = undefined, expectedTotal = undefined) {
        const res = this._do.clickDisplayedProduct(productName);
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
                .flatMap((key) => this._do.pressNumpad(mapKey(key)));
        res.push(...this._check.selectedOrderlineHas(productName, "1.00"));
        if (unitPrice) {
            res.push(...this._do.pressNumpad("Price"));
            res.push(...this._check.modeIsActive("Price"));
            res.push(...numpadWrite(unitPrice));
            res.push(...this._do.pressNumpad("Qty"));
            res.push(...this._check.modeIsActive("Qty"));
        }
        if (quantity.toString() !== "1") {
            res.push(...numpadWrite(quantity));
        }
        res.push(...this._check.selectedOrderlineHas(productName, quantity, expectedTotal));
        return res;
    }
    addMultiOrderlines(...list) {
        const steps = [];
        for (const [product, qty, price] of list) {
            steps.push(...this.addOrderline(product, qty, price));
        }
        return steps;
    }
    addCustomerNote(note) {
        const res = [];
        res.push(...this._do.clickOrderlineCustomerNoteButton());
        res.push(...TextAreaPopup._do.inputText(note));
        res.push(...TextAreaPopup._do.clickConfirm());
        res.push({
            content: "go back to the products",
            trigger: ".pos-rightheader .floor-button",
            mobile: true,
        });
        return res;
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ProductScreen", Do, Check, Execute));
