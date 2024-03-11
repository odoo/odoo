odoo.define('pos_restaurant.tour.SplitBillScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickOrderline(name, totalQuantity) {
            let trigger = `li.orderline .product-name:contains("${name}")`;
            if (totalQuantity) {
                trigger += ` ~ .info-list .info:contains("${totalQuantity}")`;
            }
            return [
                {
                    content: `click '${name}' orderline with total quantity of '${totalQuantity}'`,
                    trigger,
                },
            ];
        }
        clickBack() {
            return [
                {
                    content: 'click back button',
                    trigger: `.splitbill-screen .button.back`,
                },
            ];
        }
        clickPay() {
            return [
                {
                    content: 'click pay button',
                    trigger: `.splitbill-screen .pay-button .button`
                }
            ]
        }
    }

    class Check {
        orderlineHas(name, totalQuantity, splitQuantity) {
            return [
                {
                    content: `'${name}' orderline has total quantity of '${totalQuantity}'`,
                    trigger: `li.orderline .product-name:contains("${name}") ~ .info-list .info:contains("${totalQuantity}")`,
                    run: () => {},
                },
                {
                    content: `'${name}' orderline has '${splitQuantity}' quantity to split`,
                    trigger: `li.orderline .product-name:contains("${name}") ~ .info-list .info em:contains("${splitQuantity}")`,
                    run: () => {},
                },
            ];
        }
        subtotalIs(amount) {
            return [
                {
                    content: `total amount of split is '${amount}'`,
                    trigger: `.splitbill-screen .order-info .subtotal:contains("${amount}")`,
                },
            ];
        }
    }

    class Execute {}

    return createTourMethods('SplitBillScreen', Do, Check, Execute);
});
