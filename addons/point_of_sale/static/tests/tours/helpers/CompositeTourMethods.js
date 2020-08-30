odoo.define('point_of_sale.tour.CompositeTourMethods', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ClientListScreen } = require('point_of_sale.tour.ClientListScreenTourMethods');

    function makeFullOrder({ orderlist, customer, payment, ntimes = 1 }) {
        for (let i = 0; i < ntimes; i++) {
            ProductScreen.exec.addMultiOrderlines(...orderlist);
            if (customer) {
                ProductScreen.do.clickCustomerButton();
                ClientListScreen.exec.setClient(customer);
            }
            ProductScreen.do.clickPayButton();
            PaymentScreen.exec.pay(...payment);
            ReceiptScreen.exec.nextOrder();
        }
    }

    return { makeFullOrder };
});
