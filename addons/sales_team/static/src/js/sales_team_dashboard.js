odoo.define('sales_team.dashboard', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var Model = require('web.Model');
var session = require('web.session');
var KanbanView = require('web_kanban.KanbanView');

var QWeb = core.qweb;

var _t = core._t;
var _lt = core._lt;

var SalesTeamDashboardView = KanbanView.extend({
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
    events: {
        'click .o_dashboard_action': 'on_dashboard_action_clicked',
        'click .o_target_to_set': 'on_dashboard_target_clicked',
    },

    fetch_data: function() {
        // Overwrite this function with useful data
        return $.when();
    },

    render: function() {
        var super_render = this._super;
        var self = this;

        return this.fetch_data().then(function(result){
            self.show_demo = result && result.nb_opportunities === 0;

            var sales_dashboard = QWeb.render('sales_team.SalesDashboard', {
                widget: self,
                show_demo: self.show_demo,
                values: result,
            });
            super_render.call(self);
            $(sales_dashboard).prependTo(self.$el);
        });
    },

    on_dashboard_action_clicked: function(ev){
        ev.preventDefault();

        var $action = $(ev.currentTarget);
        var action_name = $action.attr('name');
        var action_extra = $action.data('extra');
        var additional_context = {};

        // TODO: find a better way to add defaults to search view
        if (action_name === 'calendar.action_calendar_event') {
            additional_context.search_default_mymeetings = 1;
        } else if (action_name === 'crm.crm_lead_action_activities') {
            if (action_extra === 'today') {
                additional_context.search_default_today = 1;
            } else if (action_extra === 'this_week') {
                additional_context.search_default_this_week = 1;
            } else if (action_extra === 'overdue') {
                additional_context.search_default_overdue = 1;
            }
        } else if (action_name === 'crm.action_your_pipeline') {
            if (action_extra === 'overdue') {
                additional_context['search_default_overdue'] = 1;
            } else if (action_extra === 'overdue_opp') {
                additional_context['search_default_overdue_opp'] = 1;
            }
        } else if (action_name === 'crm.crm_opportunity_report_action_graph') {
            additional_context.search_default_won = 1;
        }

        this.do_action(action_name, {additional_context: additional_context});
    },

    on_change_input_target: function(e) {
        var self = this;
        var $input = $(e.target);
        var target_name = $input.attr('name');
        var target_value = $input.val();

        if(isNaN(target_value)) {
            this.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
        } else {
            this._updated = new Model('crm.lead')
                            .call('modify_target_sales_dashboard', [target_name, parseInt(target_value)])
                            .then(function() {
                                return self.render();
                            });
        }
    },

    on_dashboard_target_clicked: function(ev){
        if (this.show_demo) {
            // The user is not allowed to modify the targets in demo mode
            return;
        }

        var self = this;
        var $target = $(ev.currentTarget);
        var target_name = $target.attr('name');
        var target_value = $target.attr('value');

        var $input = $('<input/>', {type: "text"});
        $input.attr('name', target_name);
        if (target_value) {
            $input.attr('value', target_value);
        }
        $input.on('keyup input', function(e) {
            if(e.which === $.ui.keyCode.ENTER) {
                self.on_change_input_target(e);
            }
        });
        $input.on('blur', function(e) {
            self.on_change_input_target(e);
        });

        $.when(this._updated).then(function() {
            $input.replaceAll(self.$('.o_target_to_set[name=' + target_name + ']')) // the target may have changed (re-rendering)
                  .focus()
                  .select();
        });
    },

    render_monetary_field: function(value, currency_id) {
        var currency = session.get_currency(currency_id);
        var digits_precision = currency && currency.digits;
        value = formats.format_value(value || 0, {type: "float", digits: digits_precision});
        if (currency) {
            if (currency.position === "after") {
                value += currency.symbol;
            } else {
                value = currency.symbol + value;
            }
        }
        return value;
    },
});

core.view_registry.add('sales_team_dashboard', SalesTeamDashboardView);

return SalesTeamDashboardView;

});
