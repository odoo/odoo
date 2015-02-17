odoo.define('web.ActionManager', function (require) {
"use strict";

var ControlPanel = require('web.ControlPanel');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var session = require('web.session');
var ViewManager = require('web.ViewManager');
var Widget = require('web.Widget');

var State = core.Class.extend({
    init: function(title, flags) {
        this.title = title;
        this.flags = flags;
    },
    enable: function() { return $.when(); },
    disable: function() {},
    destroy: function() {},
    get_widget: function() {},
    get_title: function() { return this.title; },
    is_headless: function() { return this.flags.headless; },
    get_action: function() {},
    get_active_view: function() {},
    get_dataset: function() {},
    get_searchview: function() {},
});

var WidgetState = State.extend({
    init: function(title, flags, widget) {
        this._super(title, flags);

        this.widget = widget;
        if (this.widget.get('title')) {
            this.title = title;
        } else {
            this.widget.set('title', title);
        }
        this.widget.on("do_search", this, function() {
            // active_search = this.control_panel.activate_search(view.created);
            // call activate search on search view
            // domain context and groupby computed are important
        });
    },
    set_cp_content: function(content) { this.cp_content = content; },
    get_cp_content: function() { return this.cp_content; },
    get_action: function() { return this.widget.action; },
    get_active_view: function() { return this.widget.active_view; },
    get_dataset: function() { return this.widget.dataset; },
    get_searchview: function() { return this.widget.get_search_view(); },
    destroy: function() { 
        if (this.cp_content && this.cp_content.searchview) {
            this.cp_content.searchview.destroy();
        }
        this.widget.destroy();
    },
    get_widget: function() {
        return this.widget;
    },
});

var FunctionState = State.extend({
    init: function(title, flags) {
        this._super(title, flags);

        this.widget = {
            view_stack: [{
                controller: { get: function () { return this.title; }}
            }]
        };
    }
});

var ActionManager = Widget.extend({
    template: "ActionManager",
    init: function(parent) {
        this._super(parent);
        this.inner_action = null;
        this.inner_widget = null;
        this.webclient = parent;
        this.dialog = null;
        this.dialog_widget = null;
        this.states = [];
        this.on('history_back', this, this.proxy('history_back'));
    },
    start: function() {
        this._super();

        // Instantiate the unique main control panel used by every widget in this.states
        this.main_control_panel = new ControlPanel(this);
        // Listen to event "switch_view" trigerred on the control panel when clicking
        // on switch buttons. Forward this event to the current inner_widget
        this.main_control_panel.on("switch_view", this, function(view_type) {
            this.inner_widget.trigger("switch_view", view_type);
        });
        // Listen to event "on_breadcrumb_click" trigerred on the control panel when
        // clicking on a part of the breadcrumbs. Call select_state for this breadcrumb.
        this.main_control_panel.on("on_breadcrumb_click", this, function(state, index) {
            this.select_state(state, index);
        });

        // Append the main control panel to the DOM (inside the ActionManager jQuery element)
        this.main_control_panel.appendTo(this.$el);
    },
    dialog_stop: function (reason) {
        if (this.dialog) {
            this.dialog.destroy(reason);
        }
        this.dialog = null;
    },
    /**
     * Add a new state to the action manager
     *
     * widget: typically, widgets added are web.ViewManager.  The action manager
     *      uses this list of widget to handle the breadcrumbs.
     * action: new action
     * options.on_reverse_breadcrumb: will be called when breadcrumb is selected
     * options.clear_breadcrumbs: boolean, if true, current widgets are destroyed
     */
    push_state: function(widget, action, options) {
        var self = this,
            to_destroy,
            old_widget = this.inner_widget,
            old_state = this.get_current_state();
        options = options || {};

        if (options.clear_breadcrumbs) {
            to_destroy = this.states;
            this.states = [];
        }
        var new_state,
            title = action.display_name || action.name;
        if (widget instanceof Widget) {
            new_state = new WidgetState(title, action.flags, widget);
        } else {
            new_state = new FunctionState(title, action.flags);
        }
        this.states.push(new_state);

        this.get_current_state().__on_reverse_breadcrumb = options.on_reverse_breadcrumb;
        this.inner_action = action;
        this.inner_widget = widget;

        // Sets the main ControlPanel state
        // AAB: temporary restrict the use of main control panel to act_window actions
        if (action.type === 'ir.actions.act_window') {
            this.main_control_panel.set_state(new_state, old_state);
            if (old_state) {
                // Save the previous state control_panel content to restore it later
                old_state.cp_content = this.main_control_panel.get_content();
            }
        }

        // Append the inner_widget and hide the old one
        return $.when(this.inner_widget.appendTo(this.$el)).done(function () {
            if (old_widget) {
                old_widget.$el.hide();
            }
            if (options.clear_breadcrumbs) {
                self.clear_states(to_destroy);
            }
        });
    },
    get_breadcrumbs: function () {
        return _.flatten(_.map(this.states, function (state) {
            if (state.widget instanceof ViewManager) {
                return state.widget.view_stack.map(function (view, index) {
                    return {
                        title: view.controller.get('title') || state.get_title(),
                        index: index,
                        widget: state,
                    };
                });
            } else {
                return { title: state.get_title(), widget: state };
            }
        }), true);
    },
    get_title: function () {
        if (this.states.length === 1) {
            // horrible hack to display the action title instead of "New" for the actions
            // that use a form view to edit something that do not correspond to a real model
            // for example, point of sale "Your Session" or most settings form,
            var state = this.states[0];
            if (state.widget instanceof ViewManager && state.widget.view_stack.length === 1) {
                return state.get_title();
            }
        }
        return _.pluck(this.get_breadcrumbs(), 'title').join(' / ');
    },
    get_states: function () {
        return this.states;
    },
    get_current_state: function() {
        return _.last(this.states);
    },
    get_inner_action: function() {
        return this.inner_action;
    },
    get_inner_widget: function() {
        return this.inner_widget;
    },
    history_back: function() {
        var state = this.get_current_state();
        if (state.widget instanceof ViewManager) {
            var nbr_views = state.widget.view_stack.length;
            if (nbr_views > 1) {
                return this.select_state(state, nbr_views - 2);
            } 
        } 
        if (this.states.length > 1) {
            state = this.states[this.states.length - 2];
            var index = state.widget.view_stack && state.widget.view_stack.length - 1;
            return this.select_state(state, index);
        }
        return $.Deferred().reject();
    },
    select_state: function(state, index) {
        var self = this;
        if (this.webclient.has_uncommitted_changes()) {
            return $.Deferred().reject();
        }

        // Client widget (-> put in ClientState?)
        if (state.__on_reverse_breadcrumb) {
            state.__on_reverse_breadcrumb();
        }
        // Set the control panel new state
        // Put in VMState?
        // Inform the ControlPanel that the current state changed (mainly restore the searchview
        // for the ViewManager to be able to do select_view, i.e. switch_mode)
        // Storing in old_state is not necessary here
        var old_state = this.get_current_state();
        this.main_control_panel.set_state(state, old_state);
        var state_index = this.states.indexOf(state),
            def = $.when(state.widget.select_view && state.widget.select_view(index));

        this.clear_states(this.states.splice(state_index + 1));
        this.inner_widget = state.widget;
        return def.done(function () {
            if (self.inner_widget.do_show) {
                self.inner_widget.do_show();
            }
        });
    },
    clear_states: function(states) {
        _.map(states || this.states, function(state) {
            state.destroy();
        });
        if (!states) {
            this.states = [];
            this.inner_widget = null;
        }
    },
    do_push_state: function(state) {
        if (!this.webclient || !this.webclient.do_push_state || this.dialog) {
            return;
        }
        state = state || {};
        if (this.inner_action) {
            if (this.inner_action._push_me === false) {
                // this action has been explicitly marked as not pushable
                return;
            }
            state.title = this.get_title();
            if(this.inner_action.type == 'ir.actions.act_window') {
                state.model = this.inner_action.res_model;
            }
            if (this.inner_action.menu_id) {
                state.menu_id = this.inner_action.menu_id;
            }
            if (this.inner_action.id) {
                state.action = this.inner_action.id;
            } else if (this.inner_action.type == 'ir.actions.client') {
                state.action = this.inner_action.tag;
                var params = {};
                _.each(this.inner_action.params, function(v, k) {
                    if(_.isString(v) || _.isNumber(v)) {
                        params[k] = v;
                    }
                });
                state = _.extend(params || {}, state);
            }
            if (this.inner_action.context) {
                var active_id = this.inner_action.context.active_id;
                if (active_id) {
                    state.active_id = active_id;
                }
                var active_ids = this.inner_action.context.active_ids;
                if (active_ids && !(active_ids.length === 1 && active_ids[0] === active_id)) {
                    // We don't push active_ids if it's a single element array containing the active_id
                    // This makes the url shorter in most cases.
                    state.active_ids = this.inner_action.context.active_ids.join(',');
                }
            }
        }
        this.webclient.do_push_state(state);
    },
    do_load_state: function(state, warm) {
        var self = this,
            action_loaded;
        if (state.action) {
            if (_.isString(state.action) && core.action_registry.contains(state.action)) {
                var action_client = {
                    type: "ir.actions.client",
                    tag: state.action,
                    params: state,
                    _push_me: state._push_me,
                };
                if (warm) {
                    this.null_action();
                }
                action_loaded = this.do_action(action_client);
            } else {
                var run_action = (!this.inner_widget || !this.inner_widget.action) || this.inner_widget.action.id !== state.action;
                if (run_action) {
                    var add_context = {};
                    if (state.active_id) {
                        add_context.active_id = state.active_id;
                    }
                    if (state.active_ids) {
                        // The jQuery BBQ plugin does some parsing on values that are valid integers.
                        // It means that if there's only one item, it will do parseInt() on it,
                        // otherwise it will keep the comma seperated list as string.
                        add_context.active_ids = state.active_ids.toString().split(',').map(function(id) {
                            return parseInt(id, 10) || id;
                        });
                    } else if (state.active_id) {
                        add_context.active_ids = [state.active_id];
                    }
                    add_context.params = state;
                    if (warm) {
                        this.null_action();
                    }
                    action_loaded = this.do_action(state.action, { additional_context: add_context });
                    $.when(action_loaded || null).done(function() {
                        self.webclient.menu.is_bound.done(function() {
                            if (self.inner_action && self.inner_action.id) {
                                self.webclient.menu.open_action(self.inner_action.id);
                            }
                        });
                    });
                }
            }
        } else if (state.model && state.id) {
            // TODO handle context & domain ?
            if (warm) {
                this.null_action();
            }
            var action = {
                res_model: state.model,
                res_id: state.id,
                type: 'ir.actions.act_window',
                views: [[false, 'form']]
            };
            action_loaded = this.do_action(action);
        } else if (state.sa) {
            // load session action
            if (warm) {
                this.null_action();
            }
            action_loaded = this.rpc('/web/session/get_session_action',  {key: state.sa}).then(function(action) {
                if (action) {
                    return self.do_action(action);
                }
            });
        }

        $.when(action_loaded || null).done(function() {
            if (self.inner_widget && self.inner_widget.do_load_state) {
                self.inner_widget.do_load_state(state, warm);
            }
        });
    },
    /**
     * Execute an OpenERP action
     *
     * @param {Number|String|Object} Can be either an action id, a client action or an action descriptor.
     * @param {Object} [options]
     * @param {Boolean} [options.clear_breadcrumbs=false] Clear the breadcrumbs history list
     * @param {Boolean} [options.replace_breadcrumb=false] Replace the current breadcrumb with the action
     * @param {Function} [options.on_reverse_breadcrumb] Callback to be executed whenever an anterior breadcrumb item is clicked on.
     * @param {Function} [options.hide_breadcrumb] Do not display this widget's title in the breadcrumb
     * @param {Function} [options.on_close] Callback to be executed when the dialog is closed (only relevant for target=new actions)
     * @param {Function} [options.action_menu_id] Manually set the menu id on the fly.
     * @param {Object} [options.additional_context] Additional context to be merged with the action's context.
     * @return {jQuery.Deferred} Action loaded
     */
    do_action: function(action, options) {
        options = _.defaults(options || {}, {
            clear_breadcrumbs: false,
            on_reverse_breadcrumb: function() {},
            hide_breadcrumb: false,
            on_close: function() {},
            action_menu_id: null,
            additional_context: {},
        });
        if (action === false) {
            action = { type: 'ir.actions.act_window_close' };
        } else if (_.isString(action) && core.action_registry.contains(action)) {
            var action_client = { type: "ir.actions.client", tag: action, params: {} };
            return this.do_action(action_client, options);
        } else if (_.isNumber(action) || _.isString(action)) {
            var self = this;
            var additional_context = {
                active_id : options.additional_context.active_id,
                active_ids : options.additional_context.active_ids,
                active_model : options.additional_context.active_model
            };
            return self.rpc("/web/action/load", { action_id: action, additional_context : additional_context }).then(function(result) {
                return self.do_action(result, options);
            });
        }

        core.bus.trigger('action', action);

        // Ensure context & domain are evaluated and can be manipulated/used
        var ncontext = new data.CompoundContext(options.additional_context, action.context || {});
        action.context = pyeval.eval('context', ncontext);
        if (action.context.active_id || action.context.active_ids) {
            // Here we assume that when an `active_id` or `active_ids` is used
            // in the context, we are in a `related` action, so we disable the
            // searchview's default custom filters.
            action.context.search_disable_custom_filters = true;
        }
        if (action.domain) {
            action.domain = pyeval.eval(
                'domain', action.domain, action.context || {});
        }

        if (!action.type) {
            console.error("No type for action", action);
            return $.Deferred().reject();
        }

        var type = action.type.replace(/\./g,'_');
        action.menu_id = options.action_menu_id;
        action.context.params = _.extend({ 'action' : action.id }, action.context.params);
        if (!(type in this)) {
            console.error("Action manager can't handle action of type " + action.type, action);
            return $.Deferred().reject();
        }

        // Special case for Dashboards, this should definitively be done upstream
        if (action.res_model === 'board.board' && action.view_mode === 'form') {
            action.target = 'inline';
            _.extend(action.flags, {
                headless: true,
                views_switcher: false,
                display_title: false,
                search_view: false,
                pager: false,
                sidebar: false,
                action_buttons: false
            });
        } else {
            var popup = action.target === 'new';
            var inline = action.target === 'inline' || action.target === 'inlineview';
            var form = _.str.startsWith(action.view_mode, 'form');
            action.flags = _.defaults(action.flags || {}, {
                views_switcher : !popup && !inline,
                search_view : !popup && !inline,
                action_buttons : !popup && !inline,
                sidebar : !popup && !inline,
                pager : (!popup || !form) && !inline,
                display_title : !popup,
                headless: (popup || inline) && form,
                search_disable_custom_filters: action.context && action.context.search_disable_custom_filters
            });
        }
        // Do not permit popups to communicate with the main control panel
        options.cp_bus = !popup && this.main_control_panel.get_bus();

        return this[type](action, options);
    },
    null_action: function() {
        this.dialog_stop();
        this.clear_states();
    },
    /**
     *
     * @param {Object} executor
     * @param {Object} executor.action original action
     * @param {Function<web.Widget>} executor.widget function used to fetch the widget instance
     * @param {String} executor.klass CSS class to add on the dialog root, if action.target=new
     * @param {Function<web.Widget, undefined>} executor.post_process cleanup called after a widget has been added as inner_widget
     * @param {Object} options
     * @return {*}
     */
    ir_actions_common: function(executor, options) {
        var widget;
        if (executor.action.target === 'new') {
            var pre_dialog = (this.dialog && !this.dialog.isDestroyed()) ? this.dialog : null;
            if (pre_dialog){
                // prevent previous dialog to consider itself closed,
                // right now, as we're opening a new one (prevents
                // reload of original form view)
                pre_dialog.off('closing', null, pre_dialog.on_close);
            }
            if (this.dialog_widget && !this.dialog_widget.isDestroyed()) {
                this.dialog_widget.destroy();
            }
            // explicitly passing a closing action to dialog_stop() prevents
            // it from reloading the original form view
            this.dialog_stop(executor.action);
            this.dialog = new Dialog(this, {
                title: executor.action.name,
                dialogClass: executor.klass,
            });

            // chain on_close triggers with previous dialog, if any
            this.dialog.on_close = function(){
                options.on_close.apply(null, arguments);
                if (pre_dialog && pre_dialog.on_close){
                    // no parameter passed to on_close as this will
                    // only be called when the last dialog is truly
                    // closing, and *should* trigger a reload of the
                    // underlying form view (see comments above)
                    pre_dialog.on_close();
                }
            };
            this.dialog.on("closing", null, this.dialog.on_close);
            widget = executor.widget();
            if (widget instanceof ViewManager) {
                _.extend(widget.flags, {
                    $buttons: this.dialog.$buttons,
                    footer_to_buttons: true,
                });
                if (widget.action.view_mode === 'form') {
                    widget.flags.headless = true;
                }
            }
            this.dialog_widget = widget;
            this.dialog_widget.setParent(this.dialog);
            var initialized = this.dialog_widget.appendTo(this.dialog.$el);
            this.dialog.open();
            return $.when(initialized);
        }
        if (this.inner_widget && this.webclient.has_uncommitted_changes()) {
            return $.Deferred().reject();
        }
        widget = executor.widget();
        this.dialog_stop(executor.action);
        return this.push_state(widget, executor.action, options);
    },
    ir_actions_act_window: function (action, options) {
        var self = this;
        return this.ir_actions_common({
            widget: function () {
                return new ViewManager(self, null, null, null, action, options.cp_bus);
            },
            action: action,
            klass: 'oe_act_window',
        }, options);
    },
    ir_actions_client: function (action, options) {
        var self = this;
        var ClientWidget = core.action_registry.get(action.tag);
        if (!ClientWidget) {
            return self.do_warn("Action Error", "Could not find client action '" + action.tag + "'.");
        }

        if (!(ClientWidget.prototype instanceof Widget)) {
            var next;
            if ((next = ClientWidget(this, action))) {
                return this.do_action(next, options);
            }
            return $.when();
        }

        return this.ir_actions_common({
            widget: function () {
                // Hide main control panel as client actions do not use it
                self.main_control_panel.do_hide();
                return new ClientWidget(self, action);
            },
            action: action,
            klass: 'oe_act_client',
        }, options).then(function () {
            if (action.tag !== 'reload') {self.do_push_state({});}
        });
    },
    ir_actions_act_window_close: function (action, options) {
        if (!this.dialog) {
            options.on_close();
        }
        this.dialog_stop();
        return $.when();
    },
    ir_actions_server: function (action, options) {
        var self = this;
        this.rpc('/web/action/run', {
            action_id: action.id,
            context: action.context || {}
        }).done(function (action) {
            self.do_action(action, options);
        });
    },
    ir_actions_report_xml: function(action, options) {
        var self = this;
        framework.blockUI();
        action = _.clone(action);
        var eval_contexts = ([session.user_context] || []).concat([action.context]);
        action.context = pyeval.eval('contexts',eval_contexts);

        // iOS devices doesn't allow iframe use the way we do it,
        // opening a new window seems the best way to workaround
        if (navigator.userAgent.match(/(iPod|iPhone|iPad)/)) {
            var params = {
                action: JSON.stringify(action),
                token: new Date().getTime()
            };
            var url = self.session.url('/web/report', params);
            framework.unblockUI();
            $('<a href="'+url+'" target="_blank"></a>')[0].click();
            return;
        }
        var c = crash_manager;
        return $.Deferred(function (d) {
            self.session.get_file({
                url: '/web/report',
                data: {action: JSON.stringify(action)},
                complete: framework.unblockUI,
                success: function(){
                    if (!self.dialog) {
                        options.on_close();
                    }
                    self.dialog_stop();
                    d.resolve();
                },
                error: function () {
                    c.rpc_error.apply(c, arguments);
                    d.reject();
                }
            });
        });
    },
    ir_actions_act_url: function (action) {
        if (action.target === 'self') {
            framework.redirect(action.url);
        } else {
            window.open(action.url, '_blank');
        }
        return $.when();
    },
});

return ActionManager;

});
