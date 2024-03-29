/** @odoo-module */

import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";

export function selectRewardLine(rewardName) {
    return [
        ...Order.hasLine({
            withClass: ".fst-italic",
            withoutClass: ".selected",
            run: "click",
            productName: rewardName,
        }),
        ...Order.hasLine({
            withClass: ".selected.fst-italic",
            productName: rewardName,
        }),
    ];
}
export function enterCode(code) {
    const steps = [
        {
            content: "open code input dialog",
            trigger: '.control-button:contains("Enter Code")',
        },
        {
            content: `enter code value: ${code}`,
            trigger: '.popup-textinput input[type="text"]',
            run: `text ${code}`,
        },
        {
            content: "confirm inputted code",
            trigger: ".popup-textinput .button.confirm",
        },
    ];
    return steps;
}
export function resetActivePrograms() {
    return [
        {
            content: "open code input dialog",
            trigger: '.control-button:contains("Reset Programs")',
        },
    ];
}
export function clickRewardButton() {
    return [
        {
            content: "open reward dialog",
            trigger: '.control-button:contains("Reward")',
        },
    ];
}
export function clickEWalletButton(text = "eWallet") {
    return [{ trigger: `.control-button:contains("${text}")` }];
}
export function claimReward(rewardName) {
    return [
        {
            content: "open reward dialog",
            trigger: '.control-button:contains("Reward")',
        },
        {
            content: "select reward",
            // There should be description because a program always has a name.
            extra_trigger: ".selection-item span:nth-child(2)",
            trigger: `.selection-item:contains("${rewardName}")`,
        },
    ];
}
export function unselectPartner() {
    return [{ trigger: ".unselect-tag" }];
}
export function clickDiscountButton() {
    return [
        {
            content: "click discount button",
            trigger: ".js_discount",
        },
    ];
}
export function clickConfirmButton() {
    return [
        {
            content: "click confirm button",
            trigger: ".button.confirm",
        },
    ];
}
export function hasRewardLine(rewardName, amount, qty) {
    return Order.hasLine({
        withClass: ".fst-italic",
        productName: rewardName,
        price: amount,
        quantity: qty,
    });
}
export function orderTotalIs(total_str) {
    return [Order.hasTotal(total_str)];
}
export function checkNoClaimableRewards() {
    return [
        {
            content: "check that no reward can be claimed",
            trigger: ".control-button:contains('Reward'):not(.highlight)",
            run: function () {}, // it's a check
        },
    ];
}
export function isRewardButtonHighlighted(isHighlighted) {
    return [
        {
            trigger: isHighlighted
                ? '.control-button.highlight:contains("Reward")'
                : '.control-button:contains("Reward"):not(:has(.highlight))',
            run: function () {}, // it's a check
        },
    ];
}
export function eWalletButtonState({ highlighted, text = "eWallet" }) {
    return [
        {
            trigger: highlighted
                ? `.control-button.highlight:contains("${text}")`
                : `.control-button:contains("${text}"):not(:has(.highlight))`,
            run: function () {}, // it's a check
        },
    ];
}
export function customerIs(name) {
    return [
        {
            trigger: `.product-screen .set-partner:contains("${name}")`,
            run: function () {},
        },
    ];
}
export function notificationMessageContains(str) {
    return [
        {
            trigger: `.o_notification span:contains("${str}")`,
            run: function () {},
        },
    ];
}
export function finalizeOrder(paymentMethod, amount) {
    return [
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod(paymentMethod),
        ...PaymentScreen.pressNumpad([...amount].join(" ")),
        ...PaymentScreen.clickValidate(),
        ...ReceiptScreen.clickNextOrder(),
    ];
}
export function removeRewardLine(name) {
    return [...selectRewardLine(name), ...ProductScreen.pressNumpad("⌫"), ...Chrome.confirmPopup()];
}
