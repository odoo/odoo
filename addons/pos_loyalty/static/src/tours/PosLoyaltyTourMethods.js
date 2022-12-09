/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Do as ProductScreenDo } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { Do as PaymentScreenDo } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { Do as ReceiptScreenDo } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { Do as ChromeDo } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";

const ProductScreen = { do: new ProductScreenDo() };
const PaymentScreen = { do: new PaymentScreenDo() };
const ReceiptScreen = { do: new ReceiptScreenDo() };
const Chrome = { do: new ChromeDo() };

class Do {
    selectRewardLine(rewardName) {
        return [
            {
                content: "select reward line",
                trigger: `.orderline.program-reward .product-name:contains("${rewardName}")`,
            },
            {
                content: "check reward line if selected",
                trigger: `.orderline.selected.program-reward .product-name:contains("${rewardName}")`,
                run: function () {}, // it's a check
            },
        ];
    }
    enterCode(code, valid = true) {
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
        if (valid) {
            steps.push({
                content: "wait for the coupon to be loaded",
                trigger: `.active-coupon:contains("(${code})")`,
                run: () => {},
            });
        }
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
                trigger: `.selection-item:contains("${rewardName}")`,
            },
        ];
    }
    unselectPartner() {
        return [{ trigger: ".unselect-tag" }];
    }
}

class Check {
    hasRewardLine(rewardName, amount, qty) {
        const steps = [
            {
                content: "check if reward line is there",
                trigger: `.orderline.program-reward span.product-name:contains("${rewardName}")`,
                run: function () {},
            },
            {
                content: "check if the reward price is correct",
                trigger: `.orderline.program-reward span.price:contains("${amount}")`,
                run: function () {},
            },
        ];
        if (qty) {
            steps.push({
                content: "check if the reward qty is correct",
                trigger: `.order .orderline.program-reward .product-name:contains("${rewardName}") ~ .info-list em:contains("${qty}")`,
                run: function () {},
            });
        }
        return steps;
    }
    orderTotalIs(total_str) {
        return [
            {
                content: "order total contains " + total_str,
                trigger: '.order .total .value:contains("' + total_str + '")',
                run: function () {}, // it's a check
            },
        ];
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
                trigger: `.actionpad button.set-partner:contains("${name}")`,
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
            ...ProductScreen.do.pressNumpad("Backspace"),
            ...Chrome.do.confirmPopup(),
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("PosLoyalty", Do, Check, Execute));
