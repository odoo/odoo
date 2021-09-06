odoo.define('flexipharmacy.ProductHistoryPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class ProductHistoryPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    ProductHistoryPopup.template = 'ProductHistoryPopup';
    ProductHistoryPopup.defaultProps = {
        cancelText: 'Close',
        title: '',
        body: '',
    };

    Registries.Component.add(ProductHistoryPopup);

    return ProductHistoryPopup;
});
 