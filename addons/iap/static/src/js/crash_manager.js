odoo.define('iap.CrashManager', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var CrashManager = require('web.CrashManager');
var Dialog = require('web.Dialog');

var _t = core._t;
var QWeb = core.qweb;

CrashManager.include({
    /**
     * @override
     */
    rpc_error: function (error) {
        if (error.data.name === "odoo.addons.iap.models.iap.InsufficientCreditError") {
            var error_data = JSON.parse(error.data.message);
            ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model:  'iap.account',
                method: 'get_credits_url',
                args: [],
                kwargs: {
                    base_url: error_data.base_url,
                    service_name: error_data.service_name,
                    credit: error_data.credit,
                }
            }).then(function (url) {
                var content = $(QWeb.render('iap.redirect_to_odoo_credit', {
                        data: error_data,
                    }))
                if (error_data.body) {
                    content.css('padding', 0);
                }
                new Dialog(this, {
                    size: 'large',
                    title: error_data.title || _t("Insufficient Balance"),
                    $content: content,
                    buttons: [
                        {text: _t('Buy credits at Odoo'), classes : "btn-primary", click: function() {
                            window.open(url, '_blank');
                        }, close:true},
                        {text: _t("Cancel"), close: true}
                    ],
                }).open();
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
