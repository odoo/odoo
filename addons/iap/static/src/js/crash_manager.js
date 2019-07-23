odoo.define('iap.CrashManager', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var InsufficientCreditError = Widget.extend({
    init: function(parent, error) {
        this._super(parent);
        this.error = error;
    },
    _getButtonMessage: function (isTrial){
        var isEnterprise = _.last(odoo.session_info.server_version_info) === 'e';
        return isTrial && isEnterprise ? _t('Start a Trial at Odoo') : _t('Buy credits at Odoo');
    },
    display: function() {
        var self = this;
        var error = this.error;

        var error_data = JSON.parse(error.data.message);
            ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model:  'iap.account',
                method: 'get_credits_url',
                args: [],
                kwargs: {
                    base_url: error_data.base_url,
                    service_name: error_data.service_name,
                    credit: error_data.credit,
                    trial: error_data.trial
                }
            }).then(function (url) {
                var content = $(QWeb.render('iap.redirect_to_odoo_credit', {
                        data: error_data,
                    }));
                if (error_data.body) {
                    content.css('padding', 0);
                }
                new Dialog(this, {
                    size: 'large',
                    title: error_data.title || _t("Insufficient Balance"),
                    $content: content,
                    buttons: [{
                        text: self._getButtonMessage(error_data.trial),
                        classes : "btn-primary",
                        click: function () {
                            window.open(url, '_blank');
                        },
                        close:true,
                    }, {
                        text: _t("Cancel"),
                        close: true,
                    }],
                }).open();
            });
    }
});

core.crash_registry.add('odoo.addons.iap.models.iap.InsufficientCreditError', InsufficientCreditError);
});
