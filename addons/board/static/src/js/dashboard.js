odoo.define('board.dashboard', function (require) {
"use strict";

var Context = require('web.Context');
var core = require('web.core');
var dataManager = require('web.data_manager');
var Dialog = require('web.Dialog');
var Domain = require('web.Domain');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var _t = core._t;
var QWeb = core.qweb;

FormView.include({
    /**
     * @override
     */
    init: function (viewInfo) {
        this._super.apply(this, arguments);
        this.controllerParams.viewID = viewInfo.view_id;
    },
});

FormController.include({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        change_layout: '_onChangeLayout',
        enable_dashboard: '_onEnableDashboard',
        save_dashboard: '_saveDashboard',
        switch_view: '_onSwitchView',
    }),
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.viewID = params.viewID;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getTitle: function () {
        if (this.inDashboard) {
            return _t("My Dashboard");
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Actually save a dashboard
     *
     * @returns {Deferred}
     */
    _saveDashboard: function () {
        var board = this.renderer.getBoard();
        var arch = QWeb.render('DashBoard.xml', _.extend({}, board));
        return this._rpc({
                route: '/web/view/add_custom',
                params: {
                    view_id: this.viewID,
                    arch: arch,
                }
            }).then(dataManager.invalidate.bind(dataManager));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onChangeLayout: function (event) {
        var self = this;
        var dialog = new Dialog(this, {
            title: _t("Edit Layout"),
            $content: QWeb.render('DashBoard.layouts', _.clone(event.data))
        });
        dialog.opened().then(function () {
            dialog.$('li').click(function () {
                var layout = $(this).attr('data-layout');
                self.renderer.changeLayout(layout);
                self._saveDashboard();
                dialog.close();
            });
        });
        dialog.open();
    },

    /**
     * @private
     */
    _onEnableDashboard: function () {
        this.inDashboard = true;
    },

    /**
     * We need to intercept switch_view event coming from sub views, because we
     * don't actually want to switch view in dashboard, we want to do a
     * do_action (which will open the record in a different breadcrumb).
     *
     * @private
     * @param {OdooEvent} event
     */
    _onSwitchView: function (event) {
        event.stopPropagation();
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: event.data.model,
            views: [[false, 'form']],
            res_id: event.data.res_id,
        });

    },

});

FormRenderer.include({
    custom_events: _.extend({}, FormRenderer.prototype.custom_events, {
        env_updated: '_onEnvUpdated',
    }),
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .oe_dashboard_column .oe_fold': '_onFoldClick',
        'click .oe_dashboard_link_change_layout': '_onChangeLayout',
        'click .oe_dashboard_column .oe_close': '_onCloseAction',
    }),

    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.noContentHelp = params.noContentHelp;
        this.actionsDescr = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {string} layout
     */
    changeLayout: function (layout) {
        var $dashboard = this.$('.oe_dashboard');
        var current_layout = $dashboard.attr('data-layout');
        if (current_layout !== layout) {
            var clayout = current_layout.split('-').length,
                nlayout = layout.split('-').length,
                column_diff = clayout - nlayout;
            if (column_diff > 0) {
                var $last_column = $();
                $dashboard.find('.oe_dashboard_column').each(function (k, v) {
                    if (k >= nlayout) {
                        $(v).find('.oe_action').appendTo($last_column);
                    } else {
                        $last_column = $(v);
                    }
                });
            }
            $dashboard.toggleClass('oe_dashboard_layout_' + current_layout + ' oe_dashboard_layout_' + layout);
            $dashboard.attr('data-layout', layout);
        }
    },

    /**
     * Returns a representation of the current dashboard
     *
     * @returns {Object}
     */
    getBoard: function () {
        var self = this;
        var board = {
            form_title : this.arch.attrs.string,
            style : this.$('.oe_dashboard').attr('data-layout'),
            columns : [],
        };
        this.$('.oe_dashboard_column').each(function () {
            var actions = [];
            $(this).find('.oe_action').each(function () {
                var actionID = $(this).attr('data-id');
                var newAttrs = _.clone(self.actionsDescr[actionID]);

                /* prepare attributes as they should be saved */
                if (newAttrs.modifiers) {
                    newAttrs.modifiers = JSON.stringify(newAttrs.modifiers);
                }
                actions.push(newAttrs);
            });
            board.columns.push(actions);
        });
        return board;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} params
     * @param {jQueryElement} params.$node
     * @param {integer} params.actionID
     * @param {Object} params.context
     * @param {any[]} params.domain
     * @param {string} params.viewType
     * @returns {Deferred}
     */
    _createController: function (params) {
        var self = this;
        var context = params.context.eval();
        return this._rpc({
                route: '/web/action/load',
                params: {action_id: params.actionID}
            })
            .then(function (action) {
                if (!action) {
                    // the action does not exist anymore
                    return $.when();
                }
                var view = _.find(action.views, function (descr) {
                    return descr[1] === params.viewType;
                });
                return self.loadViews(action.res_model, context, [view])
                           .then(function (viewsInfo) {
                    var viewInfo = viewsInfo[params.viewType];
                    var View = viewRegistry.get(params.viewType);
                    var view = new View(viewInfo, {
                        action: action,
                        context: context,
                        domain: params.domain,
                        groupBy: context.group_by,
                        modelName: action.res_model,
                        hasSelectors: false,
                    });
                    return view.getController(self).then(function (controller) {
                        return controller.appendTo(params.$node);
                    });
                });
            });
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagBoard: function (node) {
        var self = this;
        // we add the o_dashboard class to the renderer's $el. This means that
        // this function has a side effect.  This is ok because we assume that
        // once we have a '<board>' tag, we are in a special dashboard mode.
        this.$el.addClass('o_dashboard');
        this.trigger_up('enable_dashboard');

        var hasAction = _.detect(node.children, function (column) {
            return _.detect(column.children,function (element){
                return element.tag === "action"? element: false;
            });
        });
        this.$el.toggleClass('o_dashboard_nocontent', !hasAction);
        if (!hasAction) {
            var innerDiv = $('<div class="o_view_nocontent">')
                            .append(this.noContentHelp || "<div/>");
            return $('<div class="o_view_nocontent_container">')
                .append(innerDiv);
        }
        // We should start with three columns available
        node = $.extend(true, {}, node);

        // no idea why master works without this, but whatever
        if (!('layout' in node.attrs)) {
            node.attrs.layout = node.attrs.style;
        }
        for (var i = node.children.length; i < 3; i++) {
            node.children.push({
                tag: 'column',
                attrs: {},
                children: []
            });
        }

        // register actions, alongside a generated unique ID
        _.each(node.children, function (column, column_index) {
            _.each(column.children, function (action, action_index) {
                action.attrs.id = 'action_' + column_index + '_' + action_index;
                self.actionsDescr[action.attrs.id] = action.attrs;
            });
        });

        var $html = $('<div>').append($(QWeb.render('DashBoard', {node: node})));

        // render each view
        _.each(this.actionsDescr, function (action) {
            self.defs.push(self._createController({
                $node: $html.find('.oe_action[data-id=' + action.id + '] .oe_content'),
                actionID: _.str.toNumber(action.name),
                context: new Context(action.context),
                domain: Domain.prototype.stringToArray(action.domain, {}),
                viewType: action.view_mode,
            }));
        });
        $html.find('.oe_dashboard_column').sortable({
            connectWith: '.oe_dashboard_column',
            handle: '.oe_header',
            scroll: false
        }).bind('sortstop', function () {
            self.trigger_up('save_dashboard');
        });

        return $html;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChangeLayout: function () {
        var currentLayout = this.$('.oe_dashboard').attr('data-layout');
        this.trigger_up('change_layout', {currentLayout: currentLayout});
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onCloseAction: function (event) {
        var self = this;
        var $container = $(event.currentTarget).parents('.oe_action:first');
        Dialog.confirm(this, (_t("Are you sure you want to remove this item?")), {
            confirm_callback: function () {
                $container.remove();
                self.trigger_up('save_dashboard');
            },
        });
    },
    /**
     * Stops the propagation of 'update_env' events triggered by the controllers
     * instantiated by the dashboard.
     *
     * @override
     * @private
     */
    _onEnvUpdated: function (event) {
        event.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onFoldClick: function (event) {
        var $e = $(event.currentTarget);
        var $action = $e.closest('.oe_action');
        var id = $action.data('id');
        var actionAttrs = this.actionsDescr[id];

        if ($e.is('.oe_minimize')) {
            actionAttrs.fold = '1';
        } else {
            delete(actionAttrs.fold);
        }
        $e.toggleClass('oe_minimize oe_maximize');
        $action.find('.oe_content').toggle();
        this.trigger_up('save_dashboard');
    },
});

});
