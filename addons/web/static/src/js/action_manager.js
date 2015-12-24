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

/**
 * Class representing the actions of the ActionManager
 * Basic implementation for client actions that are functions
 */
var Action = core.Class.extend({
    init: function(action) {
        this.action_descr = action;
        this.title = action.display_name || action.name;
    },
    /**
     * Not implemented for client actions
     * @return {Deferred} a rejected Deferred
     */
    appendTo: function() {
        return $.Deferred().reject();
    },
    /**
     * This method should restore this previously loaded action
     * Calls on_reverse_breadcrumb callback if defined
     * @return {Deferred} resolved when widget is enabled
     */
    restore: function() {
        if (this.on_reverse_breadcrumb) {
            return this.on_reverse_breadcrumb();
        }
    },
    /**
     * Not implemented for functions
     */
    detach: function() {
    },
    /**
     * Destroyer: there is nothing to destroy in the case of a client function
     */
    destroy: function() {
    },
    /**
     * Sets the on_reverse_breadcrumb callback to be called when coming back to that action
     * @param {Function} [on_reverse_breadcrumb] the callback
     */
    set_on_reverse_breadcrumb: function(on_reverse_breadcrumb) {
        this.on_reverse_breadcrumb = on_reverse_breadcrumb;
    },
    /**
     * Stores the DOM fragment of the action
     * @param {jQuery} [fragment] the DOM fragment
     */
    set_fragment: function($fragment) {
        this.$fragment = $fragment;
    },
    /**
     * Not implemented for client actions
     */
    set_is_in_DOM: function() {
    },
    /**
     * @return {Object} the description of the action
     */
    get_action_descr: function() {
        return this.action_descr;
    },
    /**
     * @return {Object} dictionnary that will be interpreted to display the breadcrumbs
     */
    get_breadcrumbs: function() {
        return { title: this.title, action: this };
    },
    /**
     * @return {int} the number of views stacked, i.e. 0 for client functions
     */
    get_nb_views: function() {
        return 0;
    },
    /**
     * @return {jQuery} the DOM fragment of the action
     */
    get_fragment: function() {
        return this.$fragment;
    },
});
/**
 * Specialization of Action for client actions that are Widgets
 */
var WidgetAction = Action.extend({
    /**
     * Initializes the WidgetAction
     * Sets the title of the widget
     */
    init: function(action, widget) {
        this._super(action);

        this.widget = widget;
        if (!this.widget.get('title')) {
            this.widget.set('title', this.title);
        }
        this.widget.on('change:title', this, function(widget) {
            this.title = widget.get('title');
        });
    },
    /**
     * Wraps the action's widget in a container and appends it to el
     * @param {DocumentFragment} [el] where to append the widget
     * @return {Deferred} resolved when the widget is appended
     */
    appendTo: function(el) {
        this.$client_action_container = $('<div>').addClass('oe_client_action');
        this.$client_action_container.appendTo(el);
        return this.widget.appendTo(this.$client_action_container);
    },
    /**
     * Restores WidgetAction by calling do_show on its widget
     */
    restore: function() {
        var self = this;
        return $.when(this._super()).then(function() {
            return self.widget.do_show();
        });
    },
    /**
     * Detaches the client action's container from the DOM
     * @return {jQuery} the action's container
     */
    detach: function() {
        return this.$client_action_container.detach();
    },
    /**
     * Destroys the widget
     */
    destroy: function() {
        this.widget.destroy();
        this.detach();
    },
});
/**
 * Specialization of WidgetAction for window actions (i.e. ViewManagers)
 */
var ViewManagerAction = WidgetAction.extend({
    /**
     * Appends the action's widget to el
     * @param {DocumentFragment} [el] where to append the widget
     * @return {Deferred} resolved when the widget is appended
     */
    appendTo: function(el) {
        return this.widget.appendTo(el);
    },
    /**
     * Restores a ViewManagerAction
     * Switches to the requested view by calling select_view on the ViewManager
     * @param {int} [view_index] the index of the view to select
     */
    restore: function(view_index) {
        var _super = this._super.bind(this);
        return this.widget.select_view(view_index).then(function() {
            return _super();
        });
    },
    /**
     * Sets is_in_DOM on this.widget
     * @param {Boolean} [is_in_DOM] true iff the widget is attached in the DOM
     */
    set_is_in_DOM: function(is_in_DOM) {
        this.widget.is_in_DOM = is_in_DOM;
    },
    /**
     * Detaches the view_manager from the DOM
     * @return {jQuery} the view_manager's $el
     */
    detach: function() {
        return this.widget.$el.detach();
    },
    /**
     * Destroys the widget
     */
    destroy: function() { 
        this.widget.destroy();
    },
    /**
     * @return {Array} array of Objects that will be interpreted to display the breadcrumbs
     */
    get_breadcrumbs: function() {
        var self = this;
        return this.widget.view_stack.map(function (view, index) {
            return {
                title: view.controller.get('title') || self.title,
                index: index,
                action: self,
            };
        });
    },
    /**
     * @return {int} the number of views stacked in the ViewManager
     */
    get_nb_views: function() {
        return this.widget.view_stack.length;
    },
});

var ActionManager = Widget.extend({
    template: "ActionManager",
    init: function(parent) {
        this._super(parent);
        this.action_stack = [];
        this.inner_action = null;
        this.inner_widget = null;
        this.webclient = parent;
        this.dialog = null;
        this.dialog_widget = null;
        this.on('history_back', this, this.proxy('history_back'));
    },
    start: function() {
        this._super();

        // Instantiate a unique main ControlPanel used by widgets of actions in this.action_stack
        this.main_control_panel = new ControlPanel(this);
        // Listen to event "on_breadcrumb_click" trigerred on the control panel when
        // clicking on a part of the breadcrumbs. Call select_action for this breadcrumb.
        this.main_control_panel.on("on_breadcrumb_click", this, function(action, index) {
            this.select_action(action, index);
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
     * Add a new action to the action manager
     *
     * widget: typically, widgets added are openerp.web.ViewManager. The action manager
     *      uses the stack of actions to handle the breadcrumbs.
     * action_descr: new action description
     * options.on_reverse_breadcrumb: will be called when breadcrumb is clicked on
     * options.clear_breadcrumbs: boolean, if true, action stack is destroyed
     */
    push_action: function(widget, action_descr, options) {
        var self = this;
        var old_widget = this.inner_widget;
        var old_action = this.inner_action;
        var old_action_stack = this.action_stack;
        options = options || {};

        // Empty action_stack if requested
        if (options.clear_breadcrumbs) {
            this.action_stack = [];
        }

        // Instantiate the new action
        var new_action;
        if (widget instanceof ViewManager) {
            new_action = new ViewManagerAction(action_descr, widget);
        } else if (widget instanceof Widget) {
            new_action = new WidgetAction(action_descr, widget);
        } else {
            new_action = new Action(action_descr);
        }

        // Set on_reverse_breadcrumb callback on previous inner_action
        if (old_action) {
            old_action.set_on_reverse_breadcrumb(options.on_reverse_breadcrumb);
        }

        // Update action_stack (must be done before appendTo to properly
        // compute the breadcrumbs and to perform do_push_state)
        this.action_stack.push(new_action);
        this.inner_action = new_action;
        this.inner_widget = widget;

        if (widget.need_control_panel) {
            // Set the ControlPanel bus on the widget to allow it to communicate its status
            widget.set_cp_bus(this.main_control_panel.get_bus());
        }

        // render the inner_widget in a fragment, and append it to the
        // document only when it's ready
        var new_widget_fragment = document.createDocumentFragment();
        return $.when(this.inner_action.appendTo(new_widget_fragment)).done(function() {
            // Detach the fragment of the previous action and store it within the action
            if (old_action) {
                old_action.set_fragment(old_action.detach());
                old_action.set_is_in_DOM(false);
            }
            if (!widget.need_control_panel) {
                // Hide the main ControlPanel for widgets that do not use it
                self.main_control_panel.do_hide();
            }

            framework.append(self.$el, new_widget_fragment, true);
            self.inner_action.set_is_in_DOM(true);

            // Hide the old_widget as it will be removed from the DOM when it
            // is destroyed
            if (old_widget) {
                old_widget.do_hide();
            }
            if (options.clear_breadcrumbs) {
                self.clear_action_stack(old_action_stack);
            }
        }).fail(function () {
            // Destroy failed action and restore internal state
            new_action.destroy();
            self.action_stack = old_action_stack;
            self.inner_action = old_action;
            self.inner_widget = old_widget;
        });
    },
    get_breadcrumbs: function () {
        return _.flatten(_.map(this.action_stack, function (action) {
            return action.get_breadcrumbs();
        }), true);
    },
    get_title: function () {
        if (this.action_stack.length === 1) {
            // horrible hack to display the action title instead of "New" for the actions
            // that use a form view to edit something that do not correspond to a real model
            // for example, point of sale "Your Session" or most settings form,
            var action = this.action_stack[0];
            if (action.get_breadcrumbs().length === 1) {
                return action.title;
            }
        }
        var last_breadcrumb = _.last(this.get_breadcrumbs());
        return last_breadcrumb ? last_breadcrumb.title : "";
    },
    get_action_stack: function () {
        return this.action_stack;
    },
    get_inner_action: function() {
        return this.inner_action;
    },
    get_inner_widget: function() {
        return this.inner_widget;
    },
    history_back: function() {
        var nb_views = this.inner_action.get_nb_views();
        if (nb_views > 1) {
            // Stay on this action, but select the previous view
            return this.select_action(this.inner_action, nb_views - 2);
        }
        if (this.action_stack.length > 1) {
            // Select the previous action
            var action = this.action_stack[this.action_stack.length - 2];
            nb_views = action.get_nb_views();
            return this.select_action(action, nb_views - 1);
        }
        return $.Deferred().reject();
    },
    select_action: function(action, index) {
        var self = this;
        return this.webclient.clear_uncommitted_changes().then(function() {
            // Set the new inner_action/widget and update the action stack
            var old_action = self.inner_action;
            var action_index = self.action_stack.indexOf(action);
            var to_destroy = self.action_stack.splice(action_index + 1);
            self.inner_action = action;
            self.inner_widget = action.widget;

            // Hide the ControlPanel if the widget doesn't use it
            if (!self.inner_widget.need_control_panel) {
                self.main_control_panel.do_hide();
            }

            return $.when(action.restore(index)).done(function() {
                if (action !== old_action) {
                    // Clear the action stack (this also removes the current action from the DOM)
                    self.clear_action_stack(to_destroy);

                    // Append the fragment of the action to restore to self.$el
                    framework.append(self.$el, action.get_fragment(), true);
                    self.inner_action.set_is_in_DOM(true);
                }
            });
        }).fail(function() {
            return $.Deferred().reject();
        });
    },
    clear_action_stack: function(action_stack) {
        _.map(action_stack || this.action_stack, function(action) {
            action.destroy();
        });
        if (!action_stack) {
            this.action_stack = [];
            this.inner_action = null;
            this.inner_widget = null;
        }
    },
    do_push_state: function(state) {
        if (!this.webclient || !this.webclient.do_push_state || this.dialog) {
            return;
        }
        state = state || {};
        if (this.inner_action) {
            var inner_action_descr = this.inner_action.get_action_descr();
            if (inner_action_descr._push_me === false) {
                // this action has been explicitly marked as not pushable
                return;
            }
            state.title = this.get_title();
            if(inner_action_descr.type == 'ir.actions.act_window') {
                state.model = inner_action_descr.res_model;
            }
            if (inner_action_descr.menu_id) {
                state.menu_id = inner_action_descr.menu_id;
            }
            if (inner_action_descr.id) {
                state.action = inner_action_descr.id;
            } else if (inner_action_descr.type == 'ir.actions.client') {
                state.action = inner_action_descr.tag;
                var params = {};
                _.each(inner_action_descr.params, function(v, k) {
                    if(_.isString(v) || _.isNumber(v)) {
                        params[k] = v;
                    }
                });
                state = _.extend(params || {}, state);
            }
            if (inner_action_descr.context) {
                var active_id = inner_action_descr.context.active_id;
                if (active_id) {
                    state.active_id = active_id;
                }
                var active_ids = inner_action_descr.context.active_ids;
                if (active_ids && !(active_ids.length === 1 && active_ids[0] === active_id)) {
                    // We don't push active_ids if it's a single element array containing the active_id
                    // This makes the url shorter in most cases.
                    state.active_ids = inner_action_descr.context.active_ids.join(',');
                }
            }
        }
        this.webclient.do_push_state(state);
    },
    do_load_state: function(state, warm) {
        var self = this;
        var action_loaded;
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
                    action_loaded = this.do_action(state.action, { additional_context: add_context, state: state });
                    $.when(action_loaded || null).done(function() {
                        self.webclient.menu.is_bound.done(function() {
                            if (self.inner_action && self.inner_action.get_action_descr().id) {
                                self.webclient.menu.open_action(self.inner_action.get_action_descr().id);
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
                views: [[_.isNumber(state.view_id) ? state.view_id : false, 'form']]
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
                search_view : !(popup && form) && !inline,
                action_buttons : !popup && !inline,
                sidebar : !popup && !inline,
                pager : (!popup || !form) && !inline,
                display_title : !popup,
                headless: (popup || inline) && form,
                search_disable_custom_filters: action.context && action.context.search_disable_custom_filters,
            });
        }

        return this[type](action, options);
    },
    null_action: function() {
        this.dialog_stop();
        this.clear_action_stack();
    },
    /**
     *
     * @param {Object} executor
     * @param {Object} executor.action original action
     * @param {Function<instance.web.Widget>} executor.widget function used to fetch the widget instance
     * @param {String} executor.klass CSS class to add on the dialog root, if action.target=new
     * @param {Function<instance.web.Widget, undefined>} executor.post_process cleanup called after a widget has been added as inner_widget
     * @param {Object} options
     * @return {*}
     */
    ir_actions_common: function(executor, options) {
        if (executor.action.target === 'new') {
            var pre_dialog = (this.dialog && !this.dialog.isDestroyed()) ? this.dialog : null;
            if (pre_dialog){
                // prevent previous dialog to consider itself closed,
                // right now, as we're opening a new one (prevents
                // reload of original form view)
                pre_dialog.off('closed', null, pre_dialog.on_close);
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
                buttons: []
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
            this.dialog.on("closed", null, this.dialog.on_close);
            this.dialog_widget = executor.widget();
            if (this.dialog_widget instanceof ViewManager) {
                _.extend(this.dialog_widget.flags, {
                    $buttons: this.dialog.$footer,
                    footer_to_buttons: true,
                });
                if (this.dialog_widget.action.view_mode === 'form') {
                    this.dialog_widget.flags.headless = true;
                }
            }
            if (this.dialog_widget.need_control_panel) {
                // Set a fake bus to Dialogs needing a ControlPanel as they should not
                // communicate with the main ControlPanel
                this.dialog_widget.set_cp_bus(new core.Bus());
            }
            this.dialog_widget.setParent(this.dialog);
            this.dialog.open();
            
            return this.dialog_widget.appendTo(this.dialog.$el);
        }
        // Clear uncommitted changes on the current inner widget if there is one
        var self = this;
        var def = (this.inner_widget && this.webclient.clear_uncommitted_changes()) || $.when();
        return def.then(function() {
            self.dialog_stop(executor.action);
            return self.push_action(executor.widget(), executor.action, options);
        }).fail(function() {
            return $.Deferred().reject();
        });
    },
    ir_actions_act_window: function (action, options) {
        var self = this;
        return this.ir_actions_common({
            widget: function () {
                return new ViewManager(self, null, null, null, action, options);
            },
            action: action,
            klass: 'o_act_window',
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
                return new ClientWidget(self, action, options);
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
