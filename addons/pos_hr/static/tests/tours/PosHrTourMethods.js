odoo.define('pos_hr.tour.PosHrTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');
    const { SelectionPopup } = require('point_of_sale.tour.SelectionPopupTourMethods');
    const { NumberPopup } = require('point_of_sale.tour.NumberPopupTourMethods');

    class Do {
        clickLoginButton() {
            return [
                {
                    content: 'click login button',
                    trigger: '.login-overlay .login-button.select-employee',
                },
            ];
        }
        clickLockButton() {
            return [
                {
                    content: 'click lock button',
                    trigger: '.header-button .lock-button',
                },
            ];
        }
        clickCashierName() {
            return [
                {
                    content: 'click cashier name',
                    trigger: '.oe_status .username',
                }
            ]
        }
    }
    class Check {
        loginScreenIsShown() {
            return [
                {
                    content: 'login screen is shown',
                    trigger: '.login-overlay .screen-login .login-body',
                    run: () => {},
                },
            ];
        }
        cashierNameIs(name) {
            return [
                {
                    content: `logged cashier is '${name}'`,
                    trigger: `.pos .oe_status .username:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
    }
    class Execute {
        login(name, pin) {
            const res = this._do.clickLoginButton();
            res.push(...SelectionPopup._do.clickItem(name));
            if (pin) {
                res.push(...NumberPopup._do.pressNumpad(pin.split('').join(' ')));
                res.push(...NumberPopup._do.clickConfirm());
            }
            return res;
        }
    }

    return createTourMethods('PosHr', Do, Check, Execute);
});
