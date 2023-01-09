odoo.define('iap.buy_more_credits', function (require) {
'use strict';

var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var core = require('web.core');
var rpc = require('web.rpc');
const utils = require('web.utils');

var QWeb = core.qweb;

var IAPBuyMoreCreditsWidget = Widget.extend({
    className: 'o_field_iap_buy_more_credits',

    /**
     * @constructor
     * Prepares the basic rendering of edit mode by setting the root to be a
     * div.dropdown.open.
     * @see FieldChar.init
     */
    init: function (parent, data, options) {
        this._super.apply(this, arguments);
        this.service_name = options.attrs.service_name;
        this.hideService = utils.toBoolElse(options.attrs.hide_service || '', false);
    },

    /**
     * @override
     */
    start: function () {
        this.$widget = $(QWeb.render('iap.buy_more_credits', {'hideService': this.hideService}));
        this.$buyLink = this.$widget.find('.buy_credits');
        this.$widget.appendTo(this.$el);
        this.$buyLink.click(this._getLink.bind(this));
        if (!this.hideService) {
            this.el.querySelector('.o_iap_view_my_services').addEventListener('click', this._getMyServices.bind(this));
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _getLink: function () {
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

    /**
     * @private
     */
    _getMyServices() {
        return this._rpc({
            model: 'iap.account',
            method: 'get_account_url',
        }).then(url => {
            this.do_action({type: 'ir.actions.act_url', url: url});
        });
    },
});

widgetRegistry.add('iap_buy_more_credits', IAPBuyMoreCreditsWidget);

return IAPBuyMoreCreditsWidget;
});
