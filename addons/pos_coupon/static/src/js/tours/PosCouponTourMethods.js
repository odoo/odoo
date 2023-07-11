odoo.define('pos_coupon.tour.PosCouponTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { Do: ProductScreenDo } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { Do: PaymentScreenDo } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { Do: ReceiptScreenDo } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { Do: ChromeDo } = require('point_of_sale.tour.ChromeTourMethods');

    const ProductScreen = { do: new ProductScreenDo() };
    const PaymentScreen = { do: new PaymentScreenDo() };
    const ReceiptScreen = { do: new ReceiptScreenDo() };
    const Chrome = { do: new ChromeDo() };

    class Do {
        selectRewardLine(rewardName) {
            return [
                {
                    content: 'select reward line',
                    trigger: `.orderline.program-reward .product-name:contains("${rewardName}")`,
                },
                {
                    content: 'check reward line if selected',
                    trigger: `.orderline.selected.program-reward .product-name:contains("${rewardName}")`,
                    run: function () {}, // it's a check
                },
            ];
        }
        enterCode(code) {
            return [
                {
                    content: 'open code input dialog',
                    trigger: '.control-button:contains("Enter Code")',
                },
                {
                    content: `enter code value: ${code}`,
                    trigger: '.popup-textinput input[type="text"]',
                    run: `text ${code}`,
                },
                {
                    content: 'confirm inputted code',
                    trigger: '.popup-textinput .button.confirm',
                },
            ];
        }
        resetActivePrograms() {
            return [
                {
                    content: 'open code input dialog',
                    trigger: '.control-button:contains("Reset Programs")',
                },
            ];
        }
        clickDiscountButton() {
            return [
                {
                    content: 'click discount button',
                    trigger: '.js_discount',
                },
            ];
        }
        clickConfirmButton() {
            return [
                {
                    content: 'click confirm button',
                    trigger: '.button.confirm',
                },
            ];
        }
    }

    class Check {
        hasRewardLine(rewardName, amount) {
            return [
                {
                    content: 'check if reward line is there',
                    trigger: `.orderline.program-reward span.product-name:contains("${rewardName}")`,
                    run: function () {},
                },
                {
                    content: 'check if the reward price is correct',
                    trigger: `.orderline.program-reward span.price:contains("${amount}")`,
                    run: function () {},
                },
            ];
        }
        orderTotalIs(total_str) {
            return [
                {
                    content: 'order total contains ' + total_str,
                    trigger: '.order .total .value:contains("' + total_str + '")',
                    run: function () {}, // it's a check
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
                ...PaymentScreen.do.pressNumpad([...amount].join(' ')),
                ...PaymentScreen.do.clickValidate(),
                ...ReceiptScreen.do.clickNextOrder(),
            ];
        }
        removeRewardLine(name) {
            return [
                ...this.do.selectRewardLine(name),
                ...ProductScreen.do.pressNumpad('Backspace'),
                ...Chrome.do.confirmPopup(),
            ];
        }
    }

    return createTourMethods('PosCoupon', Do, Check, Execute);
});
