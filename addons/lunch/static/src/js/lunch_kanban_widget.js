odoo.define('lunch.LunchKanbanWidget', function (require) {
"use strict";

var core = require('web.core');
var relationalFields = require('web.relational_fields');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;
var FieldMany2One = relationalFields.FieldMany2One;


var LunchMany2One = FieldMany2One.extend({
    start: function () {
        this.$el.addClass('w-100');
        return this._super.apply(this, arguments);
    }
});

var LunchKanbanWidget = Widget.extend({
    template: 'LunchKanbanWidget',
    custom_events: {
        field_changed: '_onFieldChanged',
    },
    events: {
        'click .o_add_product': '_onAddProduct',
        'click .o_lunch_widget_order_button': '_onOrderNow',
        'click .o_remove_product': '_onRemoveProduct',
        'click .o_lunch_widget_unlink': '_onUnlinkOrder',
        'click .o_lunch_open_wizard': '_onLunchOpenWizard',
    },

    init: function (parent, params) {
        this._super.apply(this, arguments);

        this.is_manager = params.is_manager || false;
        this.userimage = params.userimage || '';
        this.username = params.username || '';

        this.lunchUserField = null;

        this.group_portal_id = undefined;

        this.locations = params.locations || [];
        this.userLocation = params.user_location[1] || '';

        this.lunchLocationField = this._createMany2One('locations', 'lunch.location', this.userLocation);

        this.wallet = params.wallet || 0;
        this.raw_state = params.raw_state || 'new';
        this.state = params.state || _t('To Order');
        this.lines = params.lines || [];
        this.total = params.total || 0;

        this.alerts = params.alerts || [];

        this.currency = params.currency || session.get_currency(session.company_currency_id);
    },
    willStart: function () {
        var self = this;
        var superDef = this._super.apply(this, arguments);

        var def = this._rpc({
            model: 'ir.model.data',
            method: 'xmlid_to_res_id',
            kwargs: {xmlid: 'base.group_portal'},
        }).then(function (id) {
            self.group_portal_id = id;

            if (self.is_manager) {
                self.lunchUserField = self._createMany2One('users', 'res.users', self.username, function () {
                    return [['groups_id', 'not in', [self.group_portal_id]]];
                });
            }
        });
        return Promise.all([superDef, def]);
    },
    renderElement: function () {
        this._super.apply(this, arguments);
        if (this.lunchUserField) {
            this.lunchUserField.appendTo(this.$('.o_lunch_user_field'));
        } else {
            this.$('.o_lunch_user_field').text(this.username);
        }
        this.lunchLocationField.appendTo(this.$('.o_lunch_location_field'));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _createMany2One: function (name, model, value, domain, context) {
        var fields = {};
        fields[name] = {type: 'many2one', relation: model, string: name};
        var data = {};
        data[name] = {data: {display_name: value}};

        var record = {
            id: name,
            res_id: 1,
            model: 'dummy',
            fields: fields,
            fieldsInfo: {
                default: fields,
            },
            data: data,
            getDomain: domain || function () { return []; },
            getContext: context || function () { return {}; },
        };
        var options = {
            mode: 'edit',
            noOpen: true,
            attrs: {
                can_create: false,
                can_write: false,
            }
        };
        return new LunchMany2One(this, name, record, options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onAddProduct: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('add_product', {lineId: $(ev.currentTarget).data('id')});
    },
    _onOrderNow: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('order_now', {});
    },
    _onLunchOpenWizard: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        var target = $(ev.currentTarget);
        this.trigger_up('open_wizard', {productId: target.data('product-id'), lineId: target.data('id')});
    },
    _onFieldChanged: function (ev) {
        ev.stopPropagation();

        if (ev.data.dataPointID === 'users') {
            this.trigger_up('change_user', {userId: ev.data.changes.users.id});
        } else if (ev.data.dataPointID === 'locations') {
            this.trigger_up('change_location', {locationId: ev.data.changes.locations.id});
        }
    },
    _onRemoveProduct: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('remove_product', {lineId: $(ev.currentTarget).data('id')});
    },
    _onUnlinkOrder: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.trigger_up('unlink_order', {});
    },
});

return LunchKanbanWidget;

});
