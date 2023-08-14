/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Do as ProductScreenDo } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { Do as PaymentScreenDo } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { Do as ReceiptScreenDo } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { Do as ChromeDo } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

const ProductScreen = { do: new ProductScreenDo() };
const PaymentScreen = { do: new PaymentScreenDo() };
const ReceiptScreen = { do: new ReceiptScreenDo() };
const Chrome = { do: new ChromeDo() };

class Do {
    selectRewardLine(rewardName) {
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
    enterCode(code) {
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
    resetActivePrograms() {
        return [
            {
                content: "open code input dialog",
                trigger: '.control-button:contains("Reset Programs")',
            },
        ];
    }
    clickRewardButton() {
        return [
            {
                content: "open reward dialog",
                trigger: '.control-button:contains("Reward")',
            },
        ];
    }
    clickEWalletButton(text = "eWallet") {
        return [{ trigger: `.control-button:contains("${text}")` }];
    }
    claimReward(rewardName) {
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
    unselectPartner() {
        return [{ trigger: ".unselect-tag" }];
    }
    clickDiscountButton() {
        return [
            {
                content: "click discount button",
                trigger: ".js_discount",
            },
        ];
    }
    clickConfirmButton() {
        return [
            {
                content: "click confirm button",
                trigger: ".button.confirm",
            },
        ];
    }
}

class Check {
    hasRewardLine(rewardName, amount, qty) {
        return Order.hasLine({
            withClass: ".fst-italic",
            productName: rewardName,
            price: amount,
            quantity: qty,
        });
    }
    orderTotalIs(total_str) {
        return [Order.hasTotal(total_str)];
    }
    checkNoClaimableRewards() {
        return [
            {
                content: "check that no reward can be claimed",
                trigger: ".control-button:contains('Reward'):not(.highlight)",
                run: function () {}, // it's a check
            },
        ];
    }
    isRewardButtonHighlighted(isHighlighted) {
        return [
            {
                trigger: isHighlighted
                    ? '.control-button.highlight:contains("Reward")'
                    : '.control-button:contains("Reward"):not(:has(.highlight))',
                run: function () {}, // it's a check
            },
        ];
    }
    eWalletButtonState({ highlighted, text = "eWallet" }) {
        return [
            {
                trigger: highlighted
                    ? `.control-button.highlight:contains("${text}")`
                    : `.control-button:contains("${text}"):not(:has(.highlight))`,
                run: function () {}, // it's a check
            },
        ];
    }
    customerIs(name) {
        return [
            {
                trigger: `.product-screen .set-partner:contains("${name}")`,
                run: function () {},
            },
        ];
    }
    notificationMessageContains(str) {
        return [
            {
                trigger: `.o_notification span:contains("${str}")`,
                run: function () {},
            },
        ];
    }
}

class Execute {
    constructor() {
        this.do = new Do();
        this.check = new Check();
    }
    finalizeOrder(paymentMethod, amount) {
        return [
            ...ProductScreen.do.clickPayButton(),
            ...PaymentScreen.do.clickPaymentMethod(paymentMethod),
            ...PaymentScreen.do.pressNumpad([...amount].join(" ")),
            ...PaymentScreen.do.clickValidate(),
            ...ReceiptScreen.do.clickNextOrder(),
        ];
    }
    removeRewardLine(name) {
        return [
            ...this.do.selectRewardLine(name),
            ...ProductScreen.do.pressNumpad("⌫"),
            ...Chrome.do.confirmPopup(),
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("PosLoyalty", Do, Check, Execute));
