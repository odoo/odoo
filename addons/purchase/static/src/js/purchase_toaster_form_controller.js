odoo.define('purchase.PurchaseToasterFormController', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');
var session = require('web.session');

var _t = core._t;

var PurchaseToasterFormController = FormController.include({
    /**
     * @override
     */
    _onButtonClicked: function (ev) {
        if (ev.data.attrs.class && ev.data.attrs.class.split(' ').includes('o_purchase_toaster_button')) {
            var self = this;
            this._callButtonAction(ev.data.attrs, ev.data.record).then(function () {
                self._rpc({
                    model: 'res.users',
                    method: 'read',
                    args: [[session.uid], ['email']],
                }).then(function (res) {
                    var notification = _.str.sprintf(_t("<p>A sample email has been sent to %s.</p>"), res[0].email)
                    return self.do_notify(_t("Sample Reminder Send"), notification)
                })
            }, function (res) {
                var notification = _t("No sample reminder mail send, please check the configuration.");
                return self.do_notify(_t("Sample Reminder Doesn't Sent"), notification)
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

return PurchaseToasterFormController;

});
