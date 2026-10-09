odoo.define('salon_management.SalonDashboard', function (require) {
    "use strict";
    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');
    const rpc = require("web.rpc");
    var ajax = require("web.ajax");
    const _t = core._t;
    const QWeb = core.qweb;
    const SalonDashboard = AbstractAction.extend({
        template: 'SalonDashboardMain',
        events: {
            'click .salon_spa_bookings': 'bookings',
            'click .salon_spa_sales': 'sales',
            'click .salon_spa_clients': 'clients',
            'click .salon_spa_orders': 'orders',
            'click .salon_chair': 'chairs_click',
            'click .chair_setting': 'settings_click'
        },
        init: function (parent, context) {
            this._super(parent, context);
            this.dashboards_templates = ['SalonSpaDashBoard'];

        },

        start: function () {

            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function () {
                self.render_dashboards();
                self.$el.parent().addClass('oe_background_grey');
            });

        },
        render_dashboards: function () {
            var self = this;
            var templates = ['SalonSpaDashBoard'];
            _.each(templates, function (template) {
                self.$('.spa_salon_dashboard').append(QWeb.render(template, {widget: self}));
            });
            rpc.query({
                model: "salon.booking",
                method: "get_booking_count",
                args: [0],
            })
                .then(function (result) {
                    $("#bookings_count").append("<span class='stat-digit'>" + result.bookings + "</span>");
                    $("#recent_count").append("<span class='stat-digit'>" + result.sales + "</span>");
                    $("#orders_count").append("<span class='stat-digit'>" + result.orders + "</span>");
                    $("#clients_count").append("<span class='stat-digit'>" + result.clients + "</span>");
                    ajax.jsonRpc("/salon/chairs", "call", {}).then(function (values) {
                        $('#chairs_dashboard_view').append(values);
                    });
                });
        },
        on_reverse_breadcrumb: function () {
            var self = this;
            self.$('.spa_salon_dashboard').empty();
            self.render_dashboards();
        },

        //events
        chairs_click: function (ev) {
            var self = this;
            ev.stopPropagation();
            ev.preventDefault();
            var active_id = event.target.id
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.do_action({
                name: _t("Chair Orders"),
                type: 'ir.actions.act_window',
                res_model: 'salon.order',
                view_mode: 'kanban,tree,form',
                views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                domain: [['chair_id', '=', parseInt(active_id)]],
                context: {
                    default_chair_id: parseInt(active_id)
                },
                target: 'current'
            }, options);
        },

        settings_click: function (ev) {
            var self = this;
            ev.stopPropagation();
            ev.preventDefault();
            var active_id = event.target.id
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.do_action({
                name: _t("Chair Orders"),
                type: 'ir.actions.act_window',
                res_model: 'salon.chair',
                view_mode: 'form',
                views: [[false, 'form']],
                context: {
                    default_name: active_id
                },
                target: 'current'
            }, options);
        },


        bookings: function (ev) {
            var self = this;
            ev.stopPropagation();
            ev.preventDefault();
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };

            this.do_action({
                name: _t("Salon Bookings"),
                type: 'ir.actions.act_window',
                res_model: 'salon.booking',
                view_mode: 'tree,form',
                views: [[false, 'list'], [false, 'form']],
                domain: [['state', '=', 'approved']],
                target: 'current'
            }, options);
        },

        sales: function (ev) {
            var self = this;
            ev.stopPropagation();
            ev.preventDefault();

            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };

            this.do_action({
                name: _t("Recent Works"),
                type: 'ir.actions.act_window',
                res_model: 'salon.order',
                view_mode: 'tree,form',
                views: [[false, 'list'], [false, 'form']],
                domain: [['stage_id', 'in', [3, 4]]],
                target: 'current'
            }, options);
        },
        orders: function (ev) {
            var self = this;
            ev.stopPropagation();
            ev.preventDefault();

            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };

            this.do_action({
                name: _t("Salon Orders"),
                type: 'ir.actions.act_window',
                res_model: 'salon.order',
                view_mode: 'tree,form,calendar',
                views: [[false, 'list'], [false, 'form']],
                target: 'current'
            }, options);
        },
        clients: function (e) {
            var self = this;
            e.stopPropagation();
            e.preventDefault();
            var options = {
                on_reverse_breadcrumb: self.on_reverse_breadcrumb,
            };
            self.do_action({
                name: _t("Clients"),
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                view_mode: 'tree,form',
                views: [[false, 'list'], [false, 'form']],
                domain: [['partner_salon', '=', true]],
                target: 'current'
            }, options);
        },
    });
    core.action_registry.add('salon_dashboard', SalonDashboard);
    return SalonDashboard;
});
