odoo.define('lunch.LunchKanbanWidget', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var Widget = require('web.Widget');

var qweb = core.qweb;

var LunchKanbanWidget = Widget.extend({
    template: 'LunchKanbanWidget',
    custom_events: {
    },
    events: {
        'click .o_add_money': '_onAddMoney',
        'click .o_add_product': '_onAddProduct',
        'click .o_lunch_widget_edit': '_onEditOrder',
        'click .o_lunch_widget_order_button': '_onOrderNow',
        'click .o_remove_product': '_onRemoveProduct',
        'click .o_lunch_widget_save': '_onSaveOrder',
        'click .o_lunch_widget_unlink': '_onUnlinkOrder',
        'change select': '_onUserChanged',
    },

    init: function (parent, params) {
        var self = this;
        this._super.apply(this, arguments);
        this.data = params;
        this.currency = session.get_currency(session.company_currency_id);
    },
    renderElement: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.$('select').val(this.data.username);
    },

    _onAddMoney: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('add_money', {});
    },
    _onAddProduct: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('add_product', {lineId: $(ev.currentTarget).data('id')});
    },
    _onEditOrder: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('edit_order', {});
    },
    _onOrderNow: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('order_now', {});
    },
    _onRemoveProduct: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('remove_product', {lineId: $(ev.currentTarget).data('id')});
    },
    _onSaveOrder: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('save_order', {});
    },
    _onUnlinkOrder: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('unlink_order', {});
    },
    _onUserChanged: function (ev) {
        ev.stopPropagation();

        this.trigger_up('change_user', {userId: $(ev.currentTarget).find(':selected').data('user-id')});
    }
});

return LunchKanbanWidget;

});
