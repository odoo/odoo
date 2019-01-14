odoo.define('sale_timesheet.ProjectPlan', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
var pyUtils = require('web.py_utils');
var SearchView = require('web.SearchView');

var _t = core._t;
var QWeb = core.qweb;

var ProjectPlan = AbstractAction.extend(ControlPanelMixin, {
    events: {
        "click a[type='action']": "_onClickAction",
        "click .o_timesheet_plan_redirect": '_onRedirect',
        "click .oe_stat_button": "_onClickStatButton",
        "click .o_timesheet_plan_non_billable_task": "_onClickNonBillableTask",
        "click .o_timesheet_plan_sale_timesheet_people_time .progress-bar": '_onClickEmployeeProgressbar',
    },
    /**
     * @override
     */
     init: function (parent, action) {
        this._super.apply(this, arguments);
        this.action = action;
        this.action_manager = parent;
        this.set('title', action.name || _t('Overview'));
        this.project_ids = [];
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var view_id = this.action && this.action.search_view_id && this.action.search_view_id[0];
        var def = this
            .loadViews('project.project', this.action.context || {}, [[view_id, 'search']])
            .then(function (result) {
                self.fields_view = result.search;
            });
        return $.when(this._super(), def);
    },
    /**
     * @override
     */
    start: function () {
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

        var dataset = new data.DataSetSearch(this, 'project.project');
        this.searchview = new SearchView(this, dataset, this.fields_view, options);
        this.searchview.on('search', this, this._onSearch);

        var def1 = this._super.apply(this, arguments);
        var def2 = this.searchview.appendTo($("<div>")).then(function () {
            self.$searchview_buttons = self.searchview.$buttons.contents();
        });

        return $.when(def1, def2).then(function(){
            self.searchview.do_search();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    do_show: function () {
        this._super.apply(this, arguments);
        this.searchview.do_search();
        this.action_manager.do_push_state({
            action: this.action.id,
            active_id: this.action.context.active_id,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Refresh the DOM html
     *
     * @private
     * @param {string|html} dom
     */
    _refreshPlan: function (dom) {
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
     *
     * @private
     * @param {string[]}
     * @returns {Deferred}
     */
    _fetchPlan: function (domain) {
        var self = this;
        return this._rpc({
            route:"/timesheet/plan",
            params: {domain: domain},
        }).then(function(result){
            self._refreshPlan(result.html_content);
            self._updateControlPanel(result.actions);
            self.project_ids = result.project_ids;
        });
    },
    /**
     * @private
     */
    _updateControlPanel: function (buttons) {
        // set actions button
        if (this.$buttons) {
            this.$buttons.off().destroy();
        }
        var buttons = buttons || [];
        this.$buttons = $(QWeb.render("project.plan.ControlButtons", {'buttons': buttons}));
        this.$buttons.on('click', '.o_timesheet_plan_btn_action', this._onClickControlButton.bind(this));
        // refresh control panel
        this.update_control_panel({
            cp_content: {
                $buttons: this.$buttons,
                $searchview: this.searchview.$el,
                $searchview_buttons: this.$searchview_buttons,
            },
            searchview: this.searchview,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Generate the action to execute based on the clicked target
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClickAction: function (ev) {
        var $target = this.$(ev.currentTarget);

        var action = false;
        if($target.attr('name')){ // classical case : name="action_id" type="action"
            action = $target.attr('name');
        } else { // custom case : build custom action dict
            action = {
                'name': _t('Timesheet'),
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_model': 'account.analytic.line',
            };
            // find action views
            var views = [[false, 'pivot'], [false, 'list']];
            if($target.attr('views')){
                views = JSON.parse($target.attr('views').replace(/\'/g, '"'));
            }
            action.views = views;
            action.view_mode = _.map(views, function(view_array){return view_array[1];});
            // custom domain
            var domain = [];
            if($target.attr('domain')){
                domain = JSON.parse($target.attr('domain').replace(/\'/g, '"'));
            }
            action.domain = domain;
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
    /**
     * Call the action of the action button from control panel, based on the data attribute on the button DOM
     *
     * @param {MouseEvent} event
     * @private
     */
    _onClickControlButton: function (ev) {
        var $target = $(ev.target);
        var action_id = $target.data('action-id');
        var context = $target.data('context');

        return this.do_action(action_id, {
            'additional_context': context,
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickEmployeeProgressbar: function (event) {
        var domain = $(event.currentTarget).data('domain');
        this.do_action({
            name: 'Timesheets',
            type: 'ir.actions.act_window',
            res_model: 'account.analytic.line',
            views: [[false, 'list'], [false, 'form']],
            view_type: 'list',
            view_mode: 'form',
            domain: domain || [],
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickStatButton: function (event) {
        var self = this;
        var data = $(event.currentTarget).data();
        var parameters = {
            domain: data.domain || [],
            res_model: data.resModel,
        }
        if (data.resId) {
            parameters['res_id'] = data.resId;
        }
        return this._rpc({
            route:"/timesheet/plan/action",
            params: parameters,
        }).then(function(action){
            self.do_action(action);
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickNonBillableTask: function (event) {
        var self = this;
        this.do_action({
            name: _t('Non Billable Tasks'),
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: 'project.task',
            views: [[false, 'list'], [false, 'form']],
            domain: [['project_id', 'in', this.project_ids || []], ['sale_line_id', '=', false]]
        });
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
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
    /**
     * This client action has its own search view and already listen on it. If
     * we let the event pass through, it will be caught by the action manager
     * which will do its work.  This may crash the web client, if the action
     * manager tries to notify the previous action.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onSearch: function (event) {
        event.stopPropagation();
        var session = this.getSession();
        // group by are disabled, so we don't take care of them
        var result = pyUtils.eval_domains_and_contexts({
            domains: event.data.domains,
            contexts: [session.user_context].concat(event.data.contexts)
        });

        this._fetchPlan(result.domain);
    },
});

core.action_registry.add('timesheet.plan', ProjectPlan);

return ProjectPlan;
});
