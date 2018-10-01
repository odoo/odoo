odoo.define('iap.credit.checker', function (require) {
'use strict';

var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var core = require('web.core');
var rpc = require('web.rpc');

var QWeb = core.qweb;

var IAPCreditChecker = Widget.extend({
    className: 'o_field_iap_credit_checker',

    /**
     * @constructor
     * Prepares the basic rendering of edit mode by setting the root to be a
     * div.dropdown.open.
     * @see FieldChar.init
     */
    init: function (parent, data, options) {
        this._super.apply(this, arguments);
        this.service_name = options.attrs.service_name;
    },

    /**
     * @override
     */
    start: function () {
        this.$widget = $(QWeb.render('iap.credit_checker'));
        this.$loading = this.$widget.find('.loading');
        this.$sufficient = this.$widget.find('.sufficient');
        this.$insufficient = this.$widget.find('.insufficient');
        this.$error = this.$widget.find('.error');
        this.$buyLink = this.$widget.find('.buy_credits');

        this.$widget.appendTo(this.$el);

        this.$buyLink.click(this._getLink.bind(this));

        this._getCredits();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _getCredits: function () {
        var self = this;
        this._showLoading();

        return rpc.query({
            model: 'iap.account',
            method: 'get_credits',
            args: [this.service_name],
        }, {
            shadow: true,
        }).then(function (credit) {
            if (credit > 0) self._showSufficient(credit);
            else if (credit < 0) self._showError();
            else self._showInsufficient();
        });
    },

    _getLink: function () {
        console.log(true)
        var self = this;
        return rpc.query({
            model: 'iap.account',
            method: 'get_credits_url',
            args: [this.service_name],
        }, {
            shadow: true,
        }).then(function (url) {
            return self.do_action({
                type: 'ir.actions.act_url',
                url: url,
            });
        });
    },

    _showLoading: function () {
        this.$loading.show();
        this.$sufficient.hide();
        this.$insufficient.hide();
        this.$error.hide();
    },
    _showSufficient: function (credits) {
        this.$loading.hide();
        this.$sufficient.show().find('.remaining_credits').text(credits);
        this.$insufficient.hide();
        this.$error.hide();
    },
    _showInsufficient: function () {
        this.$loading.hide();
        this.$sufficient.hide();
        this.$insufficient.show();
        this.$error.hide();
    },
    _showError: function () {
        this.$loading.hide();
        this.$sufficient.hide();
        this.$insufficient.hide();
        this.$error.show();
    },
});

widgetRegistry.add('iap_credit_checker', IAPCreditChecker);

return IAPCreditChecker;
});
