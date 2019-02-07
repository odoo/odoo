odoo.define('project_timesheet.project_plan', function (require) {
'use strict';

var ajax = require('web.ajax');
var ControlPanelMixin = require('web.ControlPanelMixin');
var Context = require('web.Context');
var core = require('web.core');
var data = require('web.data');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var PlanAction = Widget.extend(ControlPanelMixin, {
    events: {
        "click a[type='action']": "_onClickAction",
        "click .o_timesheet_plan_redirect": '_onRedirect',
        "click .oe_stat_button": "_onClickStatButton",
        "click .o_timesheet_plan_sale_timesheet_people_time .progress-bar": '_onClickEmployeeProgressbar',
    },
    init: function(parent, action, options) {
        this._super.apply(this, arguments);
        this.action = action;
        this.action_manager = parent;
    },
    willStart: function () {
        var self = this;
        var view_id = this.action && this.action.search_view_id && this.action.search_view_id[0];
        var def = this
            .loadViews('account.analytic.line', new Context(this.action.context || {}), [[view_id, 'search']])
            .then(function (result) {
                self.fields_view = result.search;
            });
        return $.when(this._super(), def);
    },
    start: function(){
        var self = this;

        // find default search from context
        var search_defaults = {};
        var context = this.action.context || [];
        _.each(context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });

        // create searchview
        var options = {
            $buttons: $("<div>"),
            action: this.action,
            disable_groupby: true,
            search_defaults: search_defaults,
        };

        var dataset = new data.DataSetSearch(this, 'account.analytic.line');
        this.searchview = new SearchView(this, dataset, this.fields_view, options);
        this.searchview.on('search', this, this._onSearch);

        var def1 = this._super.apply(this, arguments);
        var def2 = this.searchview.appendTo($("<div>")).then(function () {
            self.$searchview_buttons = self.searchview.$buttons.contents();
        });

        return $.when(def1, def2).then(function(){
            self.searchview.do_search();
            self.update_cp();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    do_show: function () {
        this._super.apply(this, arguments);
        this.update_cp();
        this.action_manager.do_push_state({
            action: this.action.id,
            active_id: this.action.context.active_id,
        });
    },
    update_cp: function () {
        this.update_control_panel({
            breadcrumbs: this.action_manager.get_breadcrumbs(),
            cp_content: {
                $buttons: this.$buttons,
                $searchview: this.searchview.$el,
                $searchview_buttons: this.$searchview_buttons,
            },
            searchview: this.searchview,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Refresh the DOM html
     * @param {string|html} dom
     * @private
     */
    _refreshPlan: function(dom){
        // TODO: Not forward port this fix on master
        var $dom = $(dom);
        $dom.find('div.o_timesheet_plan_sale_timesheet_dashboard > table.table, ' +
            'div.o_timesheet_plan_sale_timesheet_people_time > table.table, ' +
            'div.o_project_plan_project_timesheet_forecast > table.table')
            .wrap('<div class="table-responsive"></div>');
        this.$el.html($dom);
    },
    /**
     * Call controller to get the html content
     * @private
     * @returns {Deferred}
     */
    _fetchPlan: function(domain){
        var self = this;
        return this._rpc({
            route:"/timesheet/plan",
            params: {domain: domain},
        }).then(function(result){
            self._refreshPlan(result['html_content']);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Generate the action to execute based on the clicked target
     *
     * @param {MouseEvent} event
     * @private
     */
    _onClickAction: function(ev){
        var $target = this.$(ev.currentTarget);

        var action = false;
        if($target.attr('name')){ // classical case : name="action_id" type="action"
            action = $target.attr('name')
        }else{ // custom case : build custom action dict
            action = {
                'name': _t('Timesheet'),
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_model': 'account.analytic.line',
            }
            // find action views
            var views = [[false, 'pivot'], [false, 'list']];
            if($target.attr('views')){
                views = JSON.parse($target.attr('views').replace(/\'/g, '"'));
            }
            action['views'] = views;
            action['view_mode'] = _.map(views, function(view_array){return view_array[1];});
            // custom domain
            var domain = [];
            if($target.attr('domain')){
                domain = JSON.parse($target.attr('domain').replace(/\'/g, '"'));
            }
            action['domain'] = domain;
        }

        // additionnal context
        var context = {
            active_id: this.action.context.active_id,
            active_ids: this.action.context.active_ids,
            active_model: this.action.context.active_model,
        };

        if($target.attr('context')){
            var ctx_str = $target.attr('context').replace(/\'/g, '"');
            context = _.extend(context, JSON.parse(ctx_str));
        }

        this.do_action(action, {
            additional_context: context
        });
    },
    _onRedirect: function (event) {
        event.preventDefault();
        var $target = $(event.target);
        this.do_action({
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: $target.data('oe-model'),
            views: [[false, 'form']],
            res_id: $target.data('oe-id'),
        });
    },
    _onClickStatButton: function(event){
        var self = this;
        var data = $(event.currentTarget).data();
        return this._rpc({
            route:"/timesheet/plan/action",
            params: {
                domain: data['domain'],
                res_model: data['resModel'],
            },
        }).then(function(action){
            self.do_action(action);
        });
    },
    _onClickEmployeeProgressbar: function(event){
        var domain = $(event.currentTarget).data('domain');
        this.do_action({
            name: 'Timesheets',
            type: 'ir.actions.act_window',
            res_model: 'account.analytic.line',
            views: [[false, 'list'], [false, 'form']],
            view_type: 'list',
            view_mode: 'form',
            domain: domain,
        });
    },
    _onSearch: function (search_event) {
        var session = this.getSession();
        // group by are disabled, so we don't take care of them
        var result = pyeval.eval_domains_and_contexts({
            domains: search_event.data.domains,
            contexts: [session.user_context].concat(search_event.data.contexts)
        });

        this._fetchPlan(result.domain);
    },
});

core.action_registry.add('timesheet.plan', PlanAction);

});
