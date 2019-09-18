odoo.define('lunch.LunchKanbanController', function (require) {
"use strict";

/**
 * This file defines the Controller for the Lunch Kanban view, which is an
 * override of the KanbanController.
 */

var session = require('web.session');
var core = require('web.core');
var KanbanController = require('web.KanbanController');
var LunchKanbanWidget = require('lunch.LunchKanbanWidget');
var LunchPaymentDialog = require('lunch.LunchPaymentDialog');

var _t = core._t;

var LunchKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        add_product: '_onAddProduct',
        change_location: '_onLocationChanged',
        change_user: '_onUserChanged',
        open_wizard: '_onOpenWizard',
        order_now: '_onOrderNow',
        remove_product: '_onRemoveProduct',
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
        this.context = session.user_context;
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        // create a div inside o_content that will be used to wrap the lunch
        // banner and kanban renderer (this is required to get the desired
        // layout with the searchPanel to the left)
        var self = this;
        this.$('.o_content').append($('<div>').addClass('o_lunch_kanban'));
        return this._super.apply(this, arguments).then(function () {
            self.$('.o_lunch_kanban').append(self.$('.o_kanban_view'));
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
    _fetchWidgetData: function () {
        var self = this;

        return this._rpc({
            route: '/lunch/infos',
            params: {
                user_id: this.userId,
                context: this.context,
            },
        }).then(function (data) {
            self.widgetData = data;
            return self.model._updateLocation(data.user_location[0]);
        });
    },
    /**
     * Override to add the location domain (coming from the lunchKanbanWidget)
     * to the searchDomain (coming from the controlPanel).
     *
     * @override
     * @private
     */
    _getSearchDomain: function () {
        var searchDomain = this._super.apply(this, arguments) || [];
        var locationId = this.model.getCurrentLocationId();
        return searchDomain.concat([['is_available_at', 'in', [locationId]]]);
    },
    /**
     * Renders and appends the lunch banner widget.
     *
     * @private
     */
    _renderLunchKanbanWidget: function () {
        var self = this;
        var oldWidget = this.widget;
        this.widgetData.wallet = parseFloat(this.widgetData.wallet).toFixed(2);
        this.widget = new LunchKanbanWidget(this, _.extend(this.widgetData, {edit: this.editMode}));
        return this.widget.appendTo(document.createDocumentFragment()).then(function () {
            self.$('.o_lunch_kanban').prepend(self.widget.$el);
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
     * the searchPanel, also wrap the lunch widget and the kanban renderer into
     * a div, to get the desired layout.
     *
     * @override
     * @private
     */
    _update: function () {
        var def = this._fetchWidgetData().then(this._renderLunchKanbanWidget.bind(this));
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
        var self = this;

        ev.stopPropagation();

        this._rpc({
            route: '/lunch/user_location_set',
            params: {
                user_id: this.userId,
                location_id: ev.data.locationId,
                context: this.context,
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

        var ctx = this.userId ? {default_user_id: this.userId} : {};

        var options = {
            on_close: function () {
                self.reload();
            },
        };

        this.do_action({
            res_model: 'lunch.order.temp',
            name: 'Configure Your Order',
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
                context: this.context,
            },
        }).then(function () {
            self.reload();
        });
    },
});

return LunchKanbanController;

});
