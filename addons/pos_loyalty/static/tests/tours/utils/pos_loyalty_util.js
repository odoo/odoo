import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

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
    return [
        ...ProductScreen.clickControlButton("Enter Code"),
        TextInputPopup.inputText(code),
        Dialog.confirm(),
    ];
}
export function clickEWalletButton(text = "eWallet") {
    return [{ trigger: ProductScreen.controlButtonTrigger(text), run: "click" }];
}
export function claimReward(rewardName) {
    return [
        ...ProductScreen.clickControlButton("Reward"),
        {
            // There should be description because a program always has a name.
            trigger: ".selection-item span:nth-child(2)",
        },
        {
            content: "select reward",
            trigger: `.selection-item:contains("${rewardName}")`,
            run: "click",
        },
    ];
}
export function unselectPartner() {
    return [{ trigger: ".unselect-tag", run: "click" }];
}
export function clickDiscountButton() {
    return [
        ...ProductScreen.clickControlButtonMore(),
        {
            content: "click discount button",
            trigger: ".js_discount",
            run: "click",
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
    return [...Order.hasTotal(total_str)];
}
export function isRewardButtonHighlighted(isHighlighted) {
    return [
        ...ProductScreen.clickControlButtonMore(),
        {
            trigger: isHighlighted
                ? '.control-buttons button.highlight:contains("Reward")'
                : '.control-buttons button:contains("Reward"):not(:has(.highlight))',
        },
    ];
}
export function eWalletButtonState({ highlighted, text = "eWallet" }) {
    return [
        ...ProductScreen.clickControlButtonMore(),
        {
            trigger: highlighted
                ? `.control-buttons button.highlight:contains("${text}")`
                : `.control-buttons button:contains("${text}"):not(:has(.highlight))`,
        },
    ];
}
export function customerIs(name) {
    return [
        {
            trigger: `.product-screen .set-partner:contains("${name}")`,
        },
    ];
}
export function pointsAwardedAre(points_str) {
    return [
        {
            content: "loyalty points awarded " + points_str,
            trigger: '.loyalty-points-won:contains("' + points_str + '")',
            run: function () {}, // it's a check
        },
    ];
}
export function finalizeOrder(paymentMethod, amount) {
    return [
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod(paymentMethod),
        ...PaymentScreen.clickNumpad([...amount].join(" ")),
        ...PaymentScreen.clickValidate(),
        ...ReceiptScreen.clickNextOrder(),
    ];
}
export function removeRewardLine(name) {
    return [selectRewardLine(name), ProductScreen.clickNumpad("⌫"), Dialog.confirm()].flat();
}

export function checkAddedLoyaltyPoints(points) {
    return [
        {
            trigger: `.loyalty-points-won:contains("${points}")`,
        },
    ];
}
