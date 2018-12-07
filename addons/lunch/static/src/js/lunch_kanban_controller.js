odoo.define('lunch.LunchKanbanController', function (require) {
"use strict";

/**
 * This file defines the Controller for the Lunch Kanban view, which is an
 * override of the KanbanController.
 */

var core = require('web.core');
var Domain = require('web.Domain');
var KanbanController = require('web.KanbanController');
var LunchKanbanWidget = require('lunch.LunchKanbanWidget');
var LunchPaymentDialog = require('lunch.LunchPaymentDialog');
var session = require('web.session');

var qweb = core.qweb;
var _t = core._t;

var LunchKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        add_product: '_onAddProduct',
        change_location: '_onLocationChanged',
        change_user: '_onUserChanged',
        edit_order: '_onEditOrder',
        open_wizard: '_onOpenWizard',
        order_now: '_onOrderNow',
        remove_product: '_onRemoveProduct',
        save_order: '_onSaveOrder',
        unlink_order: '_onUnlinkOrder',
    }),

    /**
     * @override
     */
    init: function () {
        this.userId = null;
        this.editMode = false;
        this.updated = false;
        this.widgetData = null;
        return this._super.apply(this, arguments);
    },
    start: function () {
        this.$el.addClass('o_lunch_kanban');
        return this._super.apply(this, arguments);
    },

    _fetchPaymentInfo: function (){
        return this._rpc({
            route: '/lunch/payment_message',
        });
    },
    _fetchWidgetData: function () {
        var self = this;

        return this._rpc({
            route: '/lunch/infos',
            params: {
                user_id: this.userId,
            },
        }).then(function (data) {
            self.widgetData = data;
            self.model._updateLocation(data.user_location[0]);
        });
    },
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
    _onEditOrder: function (ev) {
        ev.stopPropagation();

        this.editMode = true;
        this.reload();
    },
    _onLocationChanged: function (ev) {
        var self = this;

        ev.stopPropagation();

        this._rpc({
            route: '/lunch/user_location_set',
            params: {
                user_id: this.userId,
                location_id: ev.data.locationId,
            },
        }).then(function () {
            self.model._updateLocation(ev.data.locationId).then(function () {
                self.reload();
            });
        });
    },
    _onOpenWizard: function (ev) {
        var self = this;
        ev.stopPropagation();

        var ctx = this.userId ? {default_user_id: this.userId}: {};

        var options = {
            on_close: function () {
                self.reload();
            },
        };

        this.do_action({
            res_model: 'lunch.order.temp',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
            context: _.extend(ctx, {default_product_id: ev.data.productId, line_id: ev.data.lineId || false}),
        }, options);
    },
    _onOrderNow: function (ev) {
        var self = this;
        ev.stopPropagation();

        this._rpc({
            route: '/lunch/pay',
            params: {
                user_id: this.userId,
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
    _onSaveOrder: function (ev) {
        ev.stopPropagation();

        this.editMode = false;
        this.reload();
    },
    _onUserChanged: function (ev) {
        ev.stopPropagation();

        var self = this;

        this.userId = ev.data.userId;
        this.model._updateUser(ev.data.userId).then(function () {
            self.reload();
        });
    },
    _onUnlinkOrder: function (ev) {
        var self = this;
        ev.stopPropagation();

        this._rpc({
            route: '/lunch/trash',
            params: {
                user_id: this.userId,
            },
        }).then(function () {
            self.reload();
        });
    },
    _orderPaid: function () {
        Dialog.alert(this, _t('Your order has been paid have a nice day'), {'title': _t('Order Paid')});
    },
    _orderNotPaid: function () {
        this._showPaymentDialog();
    },
    _showPaymentDialog: function (title) {
        var self = this;

        title = title || '';

        this._fetchPaymentInfo().then(function (data) {
            var paymentDialog = new LunchPaymentDialog(self, _.extend(data, {title: title}));
            paymentDialog.open();
        });
    },
    _update: function () {
        var self = this;

        this._fetchWidgetData().then(function () {
            if (self.widget) {
                self.widget.destroy();
            }
            self.widgetData.wallet = parseFloat(self.widgetData.wallet).toFixed(2);
            self.widget = new LunchKanbanWidget(self, _.extend(self.widgetData, {edit: self.editMode}));
            self.widget.insertBefore(self.$('.o_kanban_view'));
        });
        return this._super.apply(self, arguments);
    },
});

return LunchKanbanController;

});
