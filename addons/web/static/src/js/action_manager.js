odoo.define('web.ActionManager', function (require) {
"use strict";

var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var session = require('web.session');
var ViewManager = require('web.ViewManager');
var Widget = require('web.Widget');

var CompoundContext = data.CompoundContext;

var ActionManager = Widget.extend({
    template: "ActionManager",
    init: function(parent) {
        this._super(parent);
        this.inner_action = null;
        this.inner_widget = null;
        this.webclient = parent;
        this.dialog = null;
        this.dialog_widget = null;
        this.widgets = [];
        this.on('history_back', this, this.proxy('history_back'));
    },
    dialog_stop: function (reason) {
        if (this.dialog) {
            this.dialog.destroy(reason);
        }
        this.dialog = null;
    },
    /**
     * Add a new widget to the action manager
     *
     * widget: typically, widgets added are instance.web.ViewManager.  The action manager
     *      uses this list of widget to handle the breadcrumbs.
     * action: new action
     * options.on_reverse_breadcrumb: will be called when breadcrumb is selected
     * options.clear_breadcrumbs: boolean, if true, current widgets are destroyed
     * options.replace_breadcrumb: boolean, if true, replace current breadcrumb
     */
    push_widget: function(widget, action, options) {
        var self = this,
            to_destroy,
            old_widget = this.inner_widget;
        options = options || {};

        if (options.clear_breadcrumbs) {
            to_destroy = this.widgets;
            this.widgets = [];
        } else if (options.replace_breadcrumb) {
            to_destroy = _.last(this.widgets);
            this.widgets = _.initial(this.widgets);
        }
        if (widget instanceof Widget) {
            var title = widget.get('title') || action.display_name || action.name;
            widget.set('title', title);
            this.widgets.push(widget);
        } else {
            this.widgets.push({
                view_stack: [{
                    controller: {get: function () {return action.display_name || action.name; }},
                }],
                destroy: function () {},
            });
        }
        _.last(this.widgets).__on_reverse_breadcrumb = options.on_reverse_breadcrumb;
        this.inner_action = action;
        this.inner_widget = widget;
        return $.when(this.inner_widget.appendTo(this.$el)).done(function () {
            if ((action.target !== 'inline') && (!action.flags.headless) && widget.$header) {
                widget.$header.show();
            }
            if (old_widget) {
                old_widget.$el.hide();
            }
            if (options.clear_breadcrumbs) {
                self.clear_widgets(to_destroy);
            }
        });
    },
    get_breadcrumbs: function () {
        return _.flatten(_.map(this.widgets, function (widget) {
            if (widget instanceof ViewManager) {
                return widget.view_stack.map(function (view, index) { 
                    return {
                        title: view.controller.get('title') || widget.title,
                        index: index,
                        widget: widget,
                    }; 
                });
            } else {
                return {title: widget.get('title'), widget: widget };
            }
        }), true);
    },
    get_title: function () {
        if (this.widgets.length === 1) {
            // horrible hack to display the action title instead of "New" for the actions
            // that use a form view to edit something that do not correspond to a real model
            // for example, point of sale "Your Session" or most settings form,
            var widget = this.widgets[0];
            if (widget instanceof ViewManager && widget.view_stack.length === 1) {
                return widget.title;
            }
        }
        return _.pluck(this.get_breadcrumbs(), 'title').join(' / ');
    },
    get_widgets: function () {
        return this.widgets.slice(0);
    },
    history_back: function() {
        var widget = _.last(this.widgets);
        if (widget instanceof ViewManager) {
            var nbr_views = widget.view_stack.length;
            if (nbr_views > 1) {
                return this.select_widget(widget, nbr_views - 2);
            } 
        } 
        if (this.widgets.length > 1) {
            widget = this.widgets[this.widgets.length - 2];
            var index = widget.view_stack && widget.view_stack.length - 1;
            return this.select_widget(widget, index);
        }
        return $.Deferred().reject();
    },
    select_widget: function(widget, index) {
        var self = this;
        if (this.webclient.has_uncommitted_changes()) {
            return $.Deferred().reject();
        }
        var widget_index = this.widgets.indexOf(widget),
            def = $.when(widget.select_view && widget.select_view(index));

        return def.done(function () {
            if (widget.__on_reverse_breadcrumb) {
                widget.__on_reverse_breadcrumb();
            }
            _.each(self.widgets.splice(widget_index + 1), function (w) {
                w.destroy();
            });
            self.inner_widget = _.last(self.widgets);
            if (self.inner_widget.do_show) {
                self.inner_widget.do_show();
            }
        });
    },
    clear_widgets: function(widgets) {
        _.invoke(widgets || this.widgets, 'destroy');
        if (!widgets) {
            this.widgets = [];
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
        var ncontext = new CompoundContext(options.additional_context, action.context || {});
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
        action.menu_id = options.action_menu_id;
        action.context.params = _.extend({ 'action' : action.id }, action.context.params);
        if (!(type in this)) {
            console.error("Action manager can't handle action of type " + action.type, action);
            return $.Deferred().reject();
        }
        return this[type](action, options);
    },
    null_action: function() {
        this.dialog_stop();
        this.clear_widgets();
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
        return this.push_widget(widget, executor.action, options);
    },
    ir_actions_act_window: function (action, options) {
        var self = this;

        return this.ir_actions_common({
            widget: function () { 
                return new ViewManager(self, null, null, null, action); 
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
            widget: function () { return new ClientWidget(self, action); },
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
