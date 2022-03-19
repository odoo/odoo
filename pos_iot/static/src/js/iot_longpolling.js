/* global posmodel */
odoo.define('pos_iot.IoTLongpolling', function (require) {
'use strict';

var core = require('web.core');
var IoTLongpolling = require('iot.IoTLongpolling');
const { Gui } = require('point_of_sale.Gui');

var _t = core._t;

IoTLongpolling.include({
    _doWarnFail: function (url) {
        Gui.showPopup('IoTErrorPopup', {
            title: _t('Connection to IoT Box failed'),
            url: url,
        });
        posmodel.proxy.proxy_connection_status(url, false);
        const order = posmodel.get_order();
        if (order && order.selected_paymentline &&
            order.selected_paymentline.payment_method.use_payment_terminal === 'worldline' &&
            ['waiting', 'waitingCard', 'waitingCancel'].includes(order.selected_paymentline.payment_status)) {
            order.selected_paymentline.set_payment_status('force_done');
        }
    },

    _onSuccess: function (iot_ip, result) {
        posmodel.proxy.proxy_connection_status(iot_ip, true);
        return this._super.apply(this, arguments);
    },
    action: function (iot_ip, device_identifier, data) {
        var res = this._super.apply(this, arguments);
        res.then(function () {
            posmodel.proxy.proxy_connection_status(iot_ip, true);
        }).guardedCatch(function () {
            posmodel.proxy.proxy_connection_status(iot_ip, false);
        });
        return res;
    },
});

return IoTLongpolling;

});
