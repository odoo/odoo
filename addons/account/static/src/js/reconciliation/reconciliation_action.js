odoo.define('account.ReconciliationClientAction', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var ReconciliationModel = require('account.ReconciliationModel');
var ReconciliationRenderer = require('account.ReconciliationRenderer');
var core = require('web.core');


/**
 * Widget used as action for 'account.bank.statement' reconciliation
 */
var StatementAction = AbstractAction.extend({
    hasControlPanel: true,
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
        change_name: '_onChangeName',
        close_statement: '_onCloseStatement',
        load_more: '_onLoadMore',
        reload: 'reload',
    },
    config: _.extend({}, AbstractAction.prototype.config, {
        // used to instantiate the model
        Model: ReconciliationModel.StatementModel,
        // used to instantiate the action interface
        ActionRenderer: ReconciliationRenderer.StatementRenderer,
        // used to instantiate each widget line
        LineRenderer: ReconciliationRenderer.LineRenderer,
        // used context params
        params: ['statement_ids'],
        // number of statements/partners/accounts to display
        defaultDisplayQty: 10,
        // number of moves lines displayed in 'match' mode
        limitMoveLines: 15,
    }),

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
        this.model = new this.config.Model(this, {
            modelName: "account.reconciliation.widget",
            defaultDisplayQty: params.params && params.params.defaultDisplayQty || this.config.defaultDisplayQty,
            limitMoveLines: params.params && params.params.limitMoveLines || this.config.limitMoveLines,
        });
        this.widgets = [];
        // Adding values from the context is necessary to put this information in the url via the action manager so that
        // you can retrieve it if the person shares his url or presses f5
        _.each(params.params, function (value, name) {
            params.context[name] = name.indexOf('_ids') !== -1 ? _.map((value+'').split(), parseFloat) : value;
        });
        params.params = {};
        _.each(this.config.params, function (name) {
            if (params.context[name]) {
                params.params[name] = name.indexOf('_ids') !== -1 && _.isArray(params.context[name]) ? params.context[name].join() : params.context[name];
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
                var title = self.model.bank_statement_id  && self.model.bank_statement_id.display_name;
                self._setTitle(title);
                self.renderer = new self.config.ActionRenderer(self, self.model, {
                    'bank_statement_id': self.model.bank_statement_id,
                    'valuenow': self.model.valuenow,
                    'valuemax': self.model.valuemax,
                    'defaultDisplayQty': self.model.defaultDisplayQty,
                    'title': title,
                });
            });
    },

    reload: function() {
        // On reload destroy all rendered line widget, reload data and then rerender widget
        var self = this;
        _.each(this.widgets, function(widget) {
            widget.destroy();
        })
        this.widgets = [];
        this.model.reload()
            .then(function() {
                self.$('.o_reconciliation_lines').html('');
                self._renderLines();
                self._openFirstLine();
            });
    },

    /**
     * append the renderer and instantiate the line renderers
     *
     * @override
     */
    start: function () {
        var self = this;

        this.renderer.prependTo(self.$('.o_form_sheet'));
        this._renderLines();

        // No more lines to reconcile, trigger the rainbowman.
        var initialState = this.renderer._initialState;
        if(initialState.valuenow === initialState.valuemax){
            initialState.context = this.model.getContext();
            this.renderer.showRainbowMan(initialState);
        }else{
            // Create a notification if some lines has been reconciled automatically.
            if(initialState.valuenow > 0)
                this.renderer._renderNotifications(this.model.statement.notifications);
            this._openFirstLine();
        }

        return this._super.apply(this, arguments);
    },

    /**
     * update the control panel and breadcrumbs
     *
     * @override
     */
    do_show: function () {
        this._super.apply(this, arguments);
        if (this.action_manager) {
            this.updateControlPanel({clear: true});
            this.action_manager.do_push_state({
                action: this.params.tag,
                active_id: this.params.res_id,
            });
        }
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
            self._renderLines();
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
            this.model.changeMode(handle, 'match').always(function () {
                self._getWidget(handle).update(line);
            });
        }
        return handle;
    },
    /**
     * render line widget and append to view
     *
     * @private
     */
    _renderLines: function () {
        var self = this;
        var linesToDisplay = this.model.getStatementLines();
        _.each(linesToDisplay, function (line, handle) {
            var widget = new self.config.LineRenderer(self, self.model, line);
            widget.handle = handle;
            self.widgets.push(widget);
            widget.appendTo(self.$('.o_reconciliation_lines'));
        });
        if (this.model.hasMoreLines() === false) {
            this.renderer.hideLoadMoreButton(true);
        }
        else {
            this.renderer.hideLoadMoreButton(false);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * dispatch on the camelcased event name to model method then update the
     * line renderer with the new state. If the mode was switched from 'inactive'
     * to 'create' or 'match', the other lines switch to 'inactive' mode
     *
     * @private
     * @param {OdooEvent} event
     */
    _onAction: function (event) {
        var self = this;
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        var mode = line.mode;
        this.model[_.str.camelize(event.name)](handle, event.data.data).always(function () {
            self._getWidget(handle).update(line);
            if (mode === 'inactive' && line.mode !== 'inactive') {
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

    _onActionPartialAmount: function(event) {
        var self = this;
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        var amount = this.model.getPartialReconcileAmount(handle, event.data);
        self._getWidget(handle).updatePartialAmount(event.data.data, amount);
    },

    /**
     * call 'changeName' model method
     *
     * @private
     * @param {OdooEvent} event
     */
    _onChangeName: function (event) {
        var self = this;
        var title = event.data.data;
        this.model.changeName(title).then(function () {
            self.title = title;
            self.set("title", title);
            self.renderer.update({
                'valuenow': self.model.valuenow,
                'valuemax': self.model.valuemax,
                'title': title,
            });
        });
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
                res_model: 'account.bank.statement',
                res_id: result,
                views: [[false, 'form']],
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
            });
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
        var method = 'validate';
        this.model[method](handle).then(function (result) {
            self.renderer.update({
                'valuenow': self.model.valuenow,
                'valuemax': self.model.valuemax,
                'title': self.title,
                'time': Date.now()-self.time,
                'notifications': result.notifications,
                'context': self.model.getContext(),
            });
            _.each(result.handles, function (handle) {
                self._getWidget(handle).destroy();
                var index = _.findIndex(self.widgets, function (widget) {return widget.handle===handle;});
                self.widgets.splice(index, 1);
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
