odoo.define('account.ReconciliationClientAction', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var ReconciliationModel = require('account.ReconciliationModel');
var ReconciliationRenderer = require('account.ReconciliationRenderer');
var core = require('web.core');
var QWeb = core.qweb;


/**
 * Widget used as action for 'account.bank.statement' reconciliation
 */
var StatementAction = AbstractAction.extend({
    hasControlPanel: true,
    withSearchBar: true,
    loadControlPanel: true,
    title: core._t('Bank Reconciliation'),
    contentTemplate: 'reconciliation',
    custom_events: {
        change_mode: '_onAction',
        change_filter: '_onAction',
        change_offset: '_onAction',
        change_partner: '_onAction',
        add_proposition: '_onAction',
        remove_proposition: '_onAction',
        update_proposition: '_onAction',
        create_proposition: '_onAction',
        getPartialAmount: '_onActionPartialAmount',
        quick_create_proposition: '_onAction',
        partial_reconcile: '_onAction',
        validate: '_onValidate',
        close_statement: '_onCloseStatement',
        load_more: '_onLoadMore',
        reload: 'reload',
        search: '_onSearch',
        navigation_move:'_onNavigationMove',
    },
    config: _.extend({}, AbstractAction.prototype.config, {
        // used to instantiate the model
        Model: ReconciliationModel.StatementModel,
        // used to instantiate the action interface
        ActionRenderer: ReconciliationRenderer.StatementRenderer,
        // used to instantiate each widget line
        LineRenderer: ReconciliationRenderer.LineRenderer,
        // used context params
        params: ['statement_line_ids'],
        // number of statements/partners/accounts to display
        defaultDisplayQty: 10,
        // number of moves lines displayed in 'match' mode
        limitMoveLines: 15,
    }),

    _onNavigationMove: function (ev) {
        var non_reconciled_keys = _.keys(_.pick(this.model.lines, function(value, key, object) {return !value.reconciled}));
        var currentIndex = _.indexOf(non_reconciled_keys, ev.data.handle);
        var widget = false;
        switch (ev.data.direction) {
            case 'up':
                ev.stopPropagation();
                widget = this._getWidget(non_reconciled_keys[currentIndex-1]);
                break;
            case 'down':
                ev.stopPropagation();
                widget = this._getWidget(non_reconciled_keys[currentIndex+1]);
                break;
            case 'validate':
                ev.stopPropagation();
                widget = this._getWidget(non_reconciled_keys[currentIndex]);
                widget.$('caption .o_buttons button:visible').click();
                break;
        }
        if (widget) widget.$el.focus();
    },

    /**
     * @override
     * @param {Object} params
     * @param {Object} params.context
     *
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.action_manager = parent;
        this.params = params;
        this.controlPanelParams.modelName = 'account.bank.statement.line';
        this.model = new this.config.Model(this, {
            modelName: "account.reconciliation.widget",
            defaultDisplayQty: params.params && params.params.defaultDisplayQty || this.config.defaultDisplayQty,
            limitMoveLines: params.params && params.params.limitMoveLines || this.config.limitMoveLines,
        });
        this.widgets = [];
        // Adding values from the context is necessary to put this information in the url via the action manager so that
        // you can retrieve it if the person shares his url or presses f5
        _.each(params.params, function (value, name) {
            params.context[name] = name.indexOf('_ids') !== -1 ? _.map((value+'').split(','), parseFloat) : value;
        });
        params.params = {};
        _.each(this.config.params, function (name) {
            if (params.context[name]) {
                params.params[name] = params.context[name];
            }
        });
    },

    /**
     * instantiate the action renderer
     *
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this.model.load(this.params.context).then(this._super.bind(this));
        return def.then(function () {
                if (!self.model.context || !self.model.context.active_id) {
                    self.model.context = {'active_id': self.params.context.active_id};
                }
                if (self.params.context.journal_id) {
                    self.model.context.active_id = self.params.context.journal_id;
                }
                if (self.model.context.active_id) {
                    var promise = self._rpc({
                            model: 'account.journal',
                            method: 'read',
                            args: [self.model.context.active_id, ['display_name']],
                        });
                } else {
                    var promise = Promise.resolve();
                }
                return promise.then(function (result) {
                        var title = result && result[0] ? result[0]['display_name'] : self.params.display_name || ''
                        self._setTitle(title);
                        self.renderer = new self.config.ActionRenderer(self, self.model, {
                            'bank_statement_line_id': self.model.bank_statement_line_id,
                            'valuenow': self.model.valuenow,
                            'valuemax': self.model.valuemax,
                            'defaultDisplayQty': self.model.defaultDisplayQty,
                            'title': title,
                        });
                    });
            });
    },

    reload: function() {
        // On reload destroy all rendered line widget, reload data and then rerender widget
        var self = this;

        self.$('.o_reconciliation_lines').addClass('d-none'); // prevent the browser from recomputing css after each destroy for HUGE perf improvement on a lot of lines
        _.each(this.widgets, function(widget) {
            widget.destroy();
        });
        this.widgets = [];
        self.$('.o_reconciliation_lines').removeClass('d-none');
        return this.model.reload().then(function() {
            return self._renderLinesOrRainbow();
        });
    },

    _renderLinesOrRainbow: function() {
        var self = this;
        return self._renderLines().then(function() {
            var initialState = self.renderer._initialState;
            var valuenow = self.model.statement ? self.model.statement.value_min : initialState.valuenow;
            var valuemax = self.model.statement ? self.model.statement.value_max : initialState.valuemax;
            // No more lines to reconcile, trigger the rainbowman.
            if(valuenow === valuemax){
                initialState.valuenow = valuenow;
                initialState.context = self.model.getContext();
                self.renderer.showRainbowMan(initialState);
                self.remove_cp();
            }else{
                // Create a notification if some lines have been reconciled automatically.
                if(initialState.valuenow > 0)
                    self.renderer._renderNotifications(self.model.statement.notifications);
                self._openFirstLine();
                self.renderer.$('[data-toggle="tooltip"]').tooltip();
                self.do_show();
            }
        });
    },

    /**
     * append the renderer and instantiate the line renderers
     *
     * @override
     */
    start: function () {
        var self = this;
        var args = arguments;
        var sup = this._super;

        return this.renderer.prependTo(self.$('.o_form_sheet')).then(function() {
            return self._renderLinesOrRainbow().then(function() {
                self.do_show();
                return sup.apply(self, args);
            });
        });
    },

    /**
     * update the control panel and breadcrumbs
     *
     * @override
     */
    do_show: function () {
        this._super.apply(this, arguments);
        if (this.action_manager) {
            this.$pager = $(QWeb.render('reconciliation.control.pager', {widget: this.renderer}));
            this.updateControlPanel({
                clear: true,
                cp_content: {
                    $pager: this.$pager,
                },
            });
            this.renderer.$progress = this.$pager;
            $(this.renderer.$progress).parent().css('width', '100%').css('padding-left', '0');
        }
    },

    remove_cp: function() {
        this.updateControlPanel({
            clear: true,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} handle
     * @returns {Widget} widget line
     */
    _getWidget: function (handle) {
        return _.find(this.widgets, function (widget) {return widget.handle===handle;});
    },

    /**
     *
     */
    _loadMore: function(qty) {
        var self = this;
        return this.model.loadMore(qty).then(function () {
            return self._renderLines();
        });
    },
    /**
     * sitch to 'match' the first available line
     *
     * @private
     */
    _openFirstLine: function () {
        var self = this;

        var handle = _.compact(_.map(this.model.lines,  function (line, handle) {
                return line.reconciled ? null : handle;
            }))[0];
        if (handle) {
            var line = this.model.getLine(handle);
            this.model.changeMode(handle, 'default').then(function () {
                self._getWidget(handle).update(line);
            }).guardedCatch(function(){
                self._getWidget(handle).update(line);
            }).then(function() {
                self._getWidget(handle).$el.focus();
            }
            );
        }
        return handle;
    },

    _forceUpdate: function() {
        var self = this;
        _.each(this.model.lines, function(handle) {
            var widget = self._getWidget(handle['handle']);
            if (widget && handle.need_update) {
                widget.update(handle);
                widget.need_update = false;
            }
        })
    },
    /**
     * render line widget and append to view
     *
     * @private
     */
    _renderLines: function () {
        var self = this;
        var linesToDisplay = this.model.getStatementLines();
        var linePromises = [];
        _.each(linesToDisplay, function (line, handle) {
            var widget = new self.config.LineRenderer(self, self.model, line);
            widget.handle = handle;
            self.widgets.push(widget);
            linePromises.push(widget.appendTo(self.$('.o_reconciliation_lines')));
        });
        if (this.model.hasMoreLines() === false) {
            this.renderer.hideLoadMoreButton(true);
        }
        else {
            this.renderer.hideLoadMoreButton(false);
        }
        return Promise.all(linePromises);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * dispatch on the camelcased event name to model method then update the
     * line renderer with the new state. If the mode was switched from 'inactive'
     * to 'create' or 'match_rp' or 'match_other', the other lines switch to
     * 'inactive' mode
     *
     * @private
     * @param {OdooEvent} event
     */
    _onAction: function (event) {
        var self = this;
        var handle = event.target.handle;
        var current_line = this.model.getLine(handle);
        this.model[_.str.camelize(event.name)](handle, event.data.data).then(function () {
            var widget = self._getWidget(handle);
            if (widget) {
                widget.update(current_line);
            }
            if (current_line.mode !== 'inactive') {
                _.each(self.model.lines, function (line, _handle) {
                    if (line.mode !== 'inactive' && _handle !== handle) {
                        self.model.changeMode(_handle, 'inactive');
                        var widget = self._getWidget(_handle);
                        if (widget) {
                            widget.update(line);
                        }
                    }
                });
            }
        });
    },

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSearch: function (ev) {
        var self = this;
        ev.stopPropagation();
        this.model.domain = ev.data.domain;
        this.model.display_context = 'search';
        self.reload().then(function() {
            self.renderer._updateProgressBar({
                'valuenow': self.model.valuenow,
                'valuemax': self.model.valuemax,
            });
        });
    },

    _onActionPartialAmount: function(event) {
        var self = this;
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        var amount = this.model.getPartialReconcileAmount(handle, event.data);
        self._getWidget(handle).updatePartialAmount(event.data.data, amount);
    },

    /**
     * call 'closeStatement' model method
     *
     * @private
     * @param {OdooEvent} event
     */
    _onCloseStatement: function (event) {
        var self = this;
        return this.model.closeStatement().then(function (result) {
            self.do_action({
                name: 'Bank Statements',
                res_model: 'account.bank.statement.line',
                res_id: result,
                views: [[false, 'form']],
                type: 'ir.actions.act_window',
                view_mode: 'form',
            });
            $('.o_reward').remove();
        });
    },
    /**
     * Load more statement and render them
     *
     * @param {OdooEvent} event
     */
    _onLoadMore: function (event) {
        return this._loadMore(this.model.defaultDisplayQty);
    },
    /**
     * call 'validate' model method then destroy the
     * validated lines and update the action renderer with the new status bar
     * values and notifications then open the first available line
     *
     * @private
     * @param {OdooEvent} event
     */
    _onValidate: function (event) {
        var self = this;
        var handle = event.target.handle;
        this.model.validate(handle).then(function (result) {
            self.renderer.update({
                'valuenow': self.model.valuenow,
                'valuemax': self.model.valuemax,
                'title': self.title,
                'time': Date.now()-self.time,
                'notifications': result.notifications,
                'context': self.model.getContext(),
            });
            self._forceUpdate();
            _.each(result.handles, function (handle) {
                var widget = self._getWidget(handle);
                if (widget) {
                    widget.destroy();
                    var index = _.findIndex(self.widgets, function (widget) {return widget.handle===handle;});
                    self.widgets.splice(index, 1);
                }
            });
            // Get number of widget and if less than constant and if there are more to laod, load until constant
            if (self.widgets.length < self.model.defaultDisplayQty
                && self.model.valuemax - self.model.valuenow >= self.model.defaultDisplayQty) {
                var toLoad = self.model.defaultDisplayQty - self.widgets.length;
                self._loadMore(toLoad);
            }
            self._openFirstLine();
        });
    },
});


/**
 * Widget used as action for 'account.move.line' and 'res.partner' for the
 * manual reconciliation and mark data as reconciliate
 */
var ManualAction = StatementAction.extend({
    title: core._t('Journal Items to Reconcile'),
    withSearchBar: false,
    config: _.extend({}, StatementAction.prototype.config, {
        Model: ReconciliationModel.ManualModel,
        ActionRenderer: ReconciliationRenderer.ManualRenderer,
        LineRenderer: ReconciliationRenderer.ManualLineRenderer,
        params: ['company_ids', 'mode', 'partner_ids', 'account_ids'],
        defaultDisplayQty: 30,
        limitMoveLines: 15,
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * call 'validate' model method then destroy the
     * reconcilied lines, update the not reconcilied and update the action
     * renderer with the new status bar  values and notifications then open the
     * first available line
     *
     * @private
     * @param {OdooEvent} event
     */
    _onValidate: function (event) {
        var self = this;
        var handle = event.target.handle;
        var method = 'validate';
        this.model[method](handle).then(function (result) {
            _.each(result.reconciled, function (handle) {
                self._getWidget(handle).destroy();
            });
            _.each(result.updated, function (handle) {
                self._getWidget(handle).update(self.model.getLine(handle));
            });
            self.renderer.update({
                valuenow: _.compact(_.invoke(self.widgets, 'isDestroyed')).length,
                valuemax: self.widgets.length,
                title: self.title,
                time: Date.now()-self.time,
            });
            if(!_.any(result.updated, function (handle) {
                return self.model.getLine(handle).mode !== 'inactive';
            })) {
                self._openFirstLine();
            }
        });
    },
});

core.action_registry.add('bank_statement_reconciliation_view', StatementAction);
core.action_registry.add('manual_reconciliation_view', ManualAction);

return {
    StatementAction: StatementAction,
    ManualAction: ManualAction,
};
});
