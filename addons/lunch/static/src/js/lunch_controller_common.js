odoo.define('lunch.LunchControllerCommon', function (require) {
"use strict";

/**
 * This file defines the common events and functions used by Controllers for the Lunch view.
 */

var session = require('web.session');
var core = require('web.core');
const {Markup} = require('web.utils');
var LunchWidget = require('lunch.LunchWidget');
var LunchPaymentDialog = require('lunch.LunchPaymentDialog');

var _t = core._t;

var LunchControllerCommon = {
    custom_events: {
        add_product: '_onAddProduct',
        change_location: '_onLocationChanged',
        change_user: '_onUserChanged',
        open_wizard: '_onOpenWizard',
        order_now: '_onOrderNow',
        remove_product: '_onRemoveProduct',
        unlink_order: '_onUnlinkOrder',
    },
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.editMode = false;
        this.updated = false;
        this.widgetData = null;
        this.context = session.user_context;
        this.archiveEnabled = false;
    },
    /**
     * @override
     */
    start: function () {
        // create a div inside o_content that will be used to wrap the lunch
        // banner and renderer (this is required to get the desired
        // layout with the searchPanel to the left)
        var self = this;
        this.$('.o_content').append($('<div>').addClass('o_lunch_content'));
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_lunch_content').append(self.$('.o_lunch_view'));
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _fetchPaymentInfo: function () {
        return this._rpc({
            route: '/lunch/payment_message',
            params: {
                context: this.context,
            },
        });
    },
    async _fetchWidgetData() {
        const widgetData = await this._rpc({
            route: '/lunch/infos',
            params: {
                user_id: this.searchModel.get('userId'),
                context: this.context,
            },
        });
        widgetData.wallet = parseFloat(widgetData.wallet).toFixed(2);
        (widgetData.alerts || []).forEach(alert => { alert.message = Markup(alert.message); });
        this.widgetData = widgetData;
    },
    /**
     * Renders and appends the lunch banner widget.
     *
     * @private
     */
    _renderLunchWidget: function () {
        var oldWidget = this.widget;
        this.widget = new LunchWidget(this, Object.assign(this.widgetData, {edit: this.editMode}));
        return this.widget.appendTo(document.createDocumentFragment()).then(() => {
            this.$('.o_lunch_content').prepend(this.widget.$el);
            if (oldWidget) {
                oldWidget.destroy();
            }
        });
    },
    _showPaymentDialog: function (title) {
        var self = this;

        title = title || '';

        this._fetchPaymentInfo().then(function (data) {
            var paymentDialog = new LunchPaymentDialog(self, _.extend(data, {title: title}));
            paymentDialog.open();
        });
    },
    /**
     * Override to fetch and display the lunch data. Because of the presence of
     * the searchPanel, also wrap the lunch widget and the renderer into
     * a div, to get the desired layout.
     *
     * @override
     * @private
     */
    _update: function () {
        var def = this._fetchWidgetData().then(this._renderLunchWidget.bind(this));
        return Promise.all([def, this._super.apply(this, arguments)]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onAddProduct: function (ev) {
        var self = this;
        ev.stopPropagation();

        this._rpc({
            model: 'lunch.order',
            method: 'update_quantity',
            args: [[ev.data.lineId], 1],
        }).then(function () {
            self.reload();
        });
    },
    _onLocationChanged: function (ev) {
        ev.stopPropagation();
        this.searchModel.dispatch('setLocationId', ev.data.locationId);
    },
    _onOpenWizard: function (ev) {
        var self = this;
        ev.stopPropagation();

        var ctx = this.searchModel.get('userId') ? {default_user_id: this.searchModel.get('userId')} : {};

        var options = {
            on_close: function () {
                self.reload();
            },
        };

        var action = {
            res_model: 'lunch.order',
            name: _t('Configure Your Order'),
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
            context: _.extend(ctx, {default_product_id: ev.data.productId}),
        };

        if (ev.data.lineId) {
            action = _.extend(action, {
                res_id: ev.data.lineId,
                context: _.extend(action.context, {
                    active_id: ev.data.lineId,
                }),
            });
        }

        this.do_action(action, options);
    },
    _onOrderNow: function (ev) {
        var self = this;
        ev.stopPropagation();

        this._rpc({
            route: '/lunch/pay',
            params: {
                user_id: this.searchModel.get('userId'),
                context: this.context,
            },
        }).then(function (isPaid) {
            if (isPaid) {
                // TODO: feedback?
                self.reload();
            } else {
                self._showPaymentDialog(_t("Not enough money in your wallet"));
                self.reload();
            }
        });
    },
    _onRemoveProduct: function (ev) {
        var self = this;
        ev.stopPropagation();

        this._rpc({
            model: 'lunch.order',
            method: 'update_quantity',
            args: [[ev.data.lineId], -1],
        }).then(function () {
            self.reload();
        });
    },
    _onUserChanged: function (ev) {
        ev.stopPropagation();
        this.searchModel.dispatch('updateUserId', ev.data.userId);
    },
    _onUnlinkOrder: function (ev) {
        var self = this;
        ev.stopPropagation();

        this._rpc({
            route: '/lunch/trash',
            params: {
                user_id: this.searchModel.get('userId'),
                context: this.context,
            },
        }).then(function () {
            self.reload();
        });
    },
};

return LunchControllerCommon;

});
