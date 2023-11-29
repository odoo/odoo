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

        downPaymentFirstOrder() {
            return [
                {
                    content: `select order`,
                    trigger: `.order-row .col.name:first`,
                },
                {
                    content: `click on select the order`,
                    trigger: `.selection-item:contains('Apply a down payment')`,
                },
                {
                    content: `click on +10 button`,
                    trigger: `.mode-button.add:contains('+10')`,
                },
                {
                    content: `click on ok button`,
                    trigger: `.button.confirm`,
                }
            ];
        }

        acceptNewProduct() {
            return [
                {
                    content: `click on accept button`,
                    trigger: `.button.confirm`,
                }
            ];
        }
    }

    class CheckExt extends Check{
        checkCustomerNotes(note) {
            return [
                {
                    content: `check customer notes`,
                    trigger: `.orderline-note:contains(${note})`,
                }
            ];
        }
    }
    return createTourMethods('ProductScreen', DoExt, CheckExt, Execute);
});
