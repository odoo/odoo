import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

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
export function isRewardButtonHighlighted(isHighlighted, closeModal = true) {
    const steps = [
        ...ProductScreen.clickControlButtonMore(),
        {
            trigger: isHighlighted
                ? '.control-buttons button.highlight:contains("Reward")'
                : '.control-buttons button:contains("Reward"):not(:has(.highlight))',
        },
    ];
    if (closeModal) {
        steps.push({
            content: "Close modal after checked if reward button is highlighted",
            trigger: ".modal header .btn-close",
            run: "click",
        });
    }
    return steps;
}
export function eWalletButtonState({ highlighted, text = "eWallet", click = false }) {
    const step = {
        trigger: highlighted
            ? `.control-buttons button.highlight:contains("${text}")`
            : `.control-buttons button:contains("${text}"):not(:has(.highlight))`,
    };
    if (click) {
        step.run = "click";
    }
    const steps = [...ProductScreen.clickControlButtonMore(), step];
    if (!click) {
        steps.push({
            //Previous step is just a check. No need to keep modal openened
            trigger: ".modal header .btn-close",
            run: "click",
        });
    }
    return steps;
}
export function customerIs(name) {
    return [
        {
            trigger: `.product-screen .set-partner:contains("${name}")`,
        },
    ];
}
export function isPointsDisplayed(isDisplayed) {
    return [
        {
            trigger: isDisplayed
                ? ".loyalty-points-title"
                : "body:not(:has(.loyalty-points-title))",
        },
    ];
}
export function pointsAwardedAre(points_str) {
    return [
        {
            content: "loyalty points awarded " + points_str,
            trigger: '.loyalty-points-won:contains("' + points_str + '")',
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

export function createManualGiftCard(code, amount, date = false) {
    const steps = [
        {
            trigger: `a:contains("Sell physical gift card?")`,
            run: "click",
        },
        {
            content: `Input code '${code}'`,
            trigger: `input[id="code"]`,
            run: `edit ${code}`,
        },
        {
            content: `Input amount '${amount}'`,
            trigger: `input[id="amount"]`,
            run: `edit ${amount}`,
        },
    ];
    if (date !== false) {
        steps.push({
            content: `Input date '${date}'`,
            trigger: `.modal input.o_datetime_input.cursor-pointer.form-control.form-control-lg`,
            run: `edit ${date}`,
        });
    }
    steps.push({
        trigger: `.btn-primary:contains("Add Balance")`,
        run: "click",
    });
    return steps;
}

export function clickGiftCardProgram(name) {
    return [
        {
            content: `Click gift card program '${name}'`,
            trigger: `button.selection-item:has(span:contains("${name}"))`,
            run: "click",
        },
    ];
}

export function clickPhysicalGiftCard(code = "Sell physical gift card?") {
    return [
        {
            trigger: `ul.info-list .text-wrap:contains("${code}")`,
            run: "click",
        },
    ];
}

export function checkPartnerPoints(name, points) {
    return [
        ...ProductScreen.clickPartnerButton(),
        {
            content: `Check '${name}' has ${points} Loyalty Points`,
            trigger: `.partner-list .partner-line:contains(${name}) .partner-line-balance:contains(${points} Loyalty Point(s))`,
        },
    ];
}
