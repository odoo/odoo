odoo.define('account.ReconciliationClientAction', function (require) {
"use strict";

var ReconciliationModel = require('account.ReconciliationModel');
var ReconciliationRenderer = require('account.ReconciliationRenderer');
var ControlPanelMixin = require('web.ControlPanelMixin');
var Widget = require('web.Widget');
var core = require('web.core');


/**
 * Widget used as action for 'account.bank.statement' reconciliation
 */
var StatementAction = Widget.extend(ControlPanelMixin, {
    title: core._t('Bank reconciliation'),
    template: 'reconciliation',
    custom_events: {
        change_mode: '_onAction',
        change_filter: '_onAction',
        change_offset: '_onAction',
        change_partner: '_onAction',
        add_proposition: '_onAction',
        remove_proposition: '_onAction',
        update_proposition: '_onAction',
        create_proposition: '_onAction',
        quick_create_proposition: '_onAction',
        toggle_partial_reconcile: '_onAction',
        auto_reconciliation: '_onValidate',
        validate: '_onValidate',
        validate_all_balanced: '_onValidate',
        change_name: '_onChangeName',
    },
    config: {
        // used to instanciate the model
        Model: ReconciliationModel.StatementModel,
        // used to instanciate the action interface
        ActionRenderer: ReconciliationRenderer.StatementRenderer,
        // used to instanciate each widget line
        LineRenderer: ReconciliationRenderer.LineRenderer
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
        this.model = new this.config.Model(this, {modelName: "account.bank.statement.line"});
        this.widgets = [];
        if (!this.action_manager) {
            this.set_cp_bus(new Widget());
        }
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
                self.title = self.model.bank_statement_id ? self.model.bank_statement_id.display_name : self.title;
                self.renderer = new self.config.ActionRenderer(self, self.model, {
                    'bank_statement_id': self.model.bank_statement_id,
                    'valuenow': self.model.valuenow,
                    'valuemax': self.model.valuemax,
                    'title': self.title,
                });
            });
    },

    /**
     * append the renderer and instantiate the line renderers
     *
     * @override
     */
    start: function () {
        var self = this;

        this.set("title", this.title);
        var breadcrumbs = this.action_manager && this.action_manager.get_breadcrumbs() || [{ title: this.title, action: this }];
        this.update_control_panel({breadcrumbs: breadcrumbs, search_view_hidden: true}, {clear: true});

        this.renderer.prependTo(self.$('.o_form_sheet'));
        _.each(this.model.lines, function (line, handle) {
            var widget = new self.config.LineRenderer(self, self.model, line);
            widget.handle = handle;
            self.widgets.push(widget);
            widget.appendTo(self.$('.o_reconciliation_lines'));
        });
        this._openFirstLine();
    },

    /**
     * update the control panel and breadcrumbs
     *
     * @override
     */
    do_show: function () {
        this._super.apply(this, arguments);
        if (this.action_manager) {
            var breadcrumbs = this.action_manager && this.action_manager.get_breadcrumbs() || [{ title: this.title, action: this }];
            while (breadcrumbs.length) {
                if (breadcrumbs[breadcrumbs.length-1].action.widget === this) {
                    break;
                }
                breadcrumbs.pop();
            }
            this.update_control_panel({breadcrumbs: breadcrumbs, search_view_hidden: true}, {clear: true});
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
                        self._getWidget(_handle).update(line);
                    }
                });
            }
        });
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
     * call 'validate' or 'autoReconciliation' model method then destroy the
     * validated lines and update the action renderer with the new status bar 
     * values and notifications then open the first available line
     *
     * @private
     * @param {OdooEvent} event
     */
    _onValidate: function (event) {
        var self = this;
        var handle = event.target.handle;
        var method = event.name.indexOf('auto_reconciliation') === -1 ? 'validate' : 'autoReconciliation';
        this.model[method](handle).then(function (result) {
            self.renderer.update({
                'valuenow': self.model.valuenow,
                'valuemax': self.model.valuemax,
                'title': self.title,
                'time': Date.now()-self.time,
                'notifications': result.notifications,
            });
            _.each(result.handles, function (handle) {
                self._getWidget(handle).destroy();
            });
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
    config: {
        Model: ReconciliationModel.ManualModel,
        ActionRenderer: ReconciliationRenderer.ManualRenderer,
        LineRenderer: ReconciliationRenderer.ManualLineRenderer
    },
    /**
     * call 'validate' or 'autoReconciliation' model method then destroy the
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
        var method = event.name.indexOf('auto_reconciliation') === -1 ? 'validate' : 'autoReconciliation';
        this.model[method](handle).then(function (result) {
            self.renderer.update({
                'valuenow': self.model.valuenow,
                'valuemax': self.model.valuemax,
                'title': self.title,
                'time': Date.now()-self.time,
                'notifications': result.notifications,
            });
            _.each(result.reconciled, function (handle) {
                self._getWidget(handle).destroy();
            });
            _.each(result.updated, function (handle) {
                self._getWidget(handle).update(self.model.getLine(handle));
            });
            self._openFirstLine();
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
