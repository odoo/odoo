odoo.define('pos_sale.tour.ProductScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { Do, Check, Execute } = require('point_of_sale.tour.ProductScreenTourMethods');

    class DoExt extends Do {
        clickQuotationButton() {
            return [
                {
                    content: 'click quotation button',
                    trigger: '.o_sale_order_button',
                }
            ];
        }

        selectFirstOrder() {
            return [
                {
                    content: `select order`,
                    trigger: `.order-row .col.name:first`,
                },
                {
                    content: `click on select the order`,
                    trigger: `.selection-item:contains('Settle the order')`,
                }
            ];
        }

        selectNthOrder(n) {
            return [
                {
                    content: `select order`,
                    trigger: `.order-list .order-row:nth-child(${n})`,
                },
                {
                    content: `click on select the order`,
                    trigger: `.selection-item:contains('Settle the order')`,
                }
            ];
        }
    }
    return createTourMethods('ProductScreen', DoExt, Check, Execute);
});
