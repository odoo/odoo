odoo.define('pos_hr.PointOfSaleUI', function (require) {
    'use strict';

    const PointOfSaleUI = require('point_of_sale.PointOfSaleUI');
    const HeaderLockButton = require('pos_hr.HeaderLockButton');
    const LoginScreen = require('pos_hr.LoginScreen');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { patch } = require('web.utils');

    patch(PointOfSaleUI.prototype, 'pos_hr', {
        setup() {
            useBarcodeReader(this.env.model.barcodeReader, {
                cashier: this._barcodeCashierAction,
            });
            this._super(...arguments);
        },
        async _barcodeCashierAction(code) {
            let theEmployee;
            for (const employee of this.env.model.getRecords('hr.employee')) {
                if (employee._extras.hashedBarcode === Sha1.hash(code.code)) {
                    theEmployee = employee;
                    break;
                }
            }
            if (!theEmployee) return;
            this.env.model.actionHandler({ name: 'actionSelectEmployee', args: [{ selected: theEmployee }] });
        },
    });

    patch(PointOfSaleUI, 'pos_hr', {
        components: { ...PointOfSaleUI.components, HeaderLockButton, LoginScreen },
    });

    return PointOfSaleUI;
});
