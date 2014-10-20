/*---------------------------------------------------------
 * OpenERP web library
 *---------------------------------------------------------*/

(function() {
"use strict";

var instance = openerp;
openerp.web.views = {};
var QWeb = instance.web.qweb,
    _t = instance.web._t;

instance.web.ActionManager = instance.web.Widget.extend({
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
     * clear_breadcrumbs: boolean, if true, current widgets are destroyed
     */
    push_widget: function(widget, action, clear_breadcrumbs) {
        var self = this,
            old_widget = this.inner_widget;

        if (clear_breadcrumbs) {
            var to_destroy = this.widgets;
            this.widgets = [];
        }
        if (widget instanceof instance.web.ViewManager) {
            this.widgets.push(widget);
        } else {
            this.widgets.push({
                view_stack: [{
                    controller: {get: function () {return action.display_name || action.name; }},
                }],
                destroy: function () {},
            });
        }
        this.inner_action = action;
        this.inner_widget = widget;
        return $.when(this.inner_widget.appendTo(this.$el)).done(function () {
            (action.target !== 'inline') && (!action.flags.headless) && widget.$header && widget.$header.show();
            old_widget && old_widget.$el.hide();
            if (clear_breadcrumbs) {
                self.clear_widgets(to_destroy)
            }
        });
    },
    get_breadcrumbs: function () {
        return _.flatten(_.map(this.widgets, function (vm) {
            return vm.view_stack.map(function (view, index) { 
                return {
                    title: view.controller.get('title') || vm.title,
                    index: index,
                    view_manager: vm,
                }; 
            });
        }), true);
    },
    history_back: function() {
        var widget = _.last(this.widgets),
            nbr_views = widget.view_stack.length;
        if (nbr_views > 1) {
            this.select_widget(widget, nbr_views - 2);
        } else if (this.widgets.length > 1) {
            widget = this.widgets[this.widgets.length -2];
            nbr_views = widget.view_stack.length;
            this.select_view(widgets, nbr_views - 2)
        }
    },
    select_widget: function(widget, index) {
        var self = this;
        if (this.webclient.has_uncommitted_changes()) {
            return false;
        }
        var vm_index = this.widgets.indexOf(widget);
        if (widget.select_view) {
            widget.select_view(index).done(function () {
                _.each(self.widgets.splice(vm_index + 1), function (vm) {
                    vm.destroy();
                });
                self.inner_widget = _.last(self.widgets);
                self.inner_widget.display_breadcrumbs();
                self.inner_widget.$el.show();
            });
        }
    },
    clear_widgets: function(vms) {
        _.each(vms || this.widgets, function (vm) {
            vm.destroy();
        });
        if (!vms) {
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
            state.title = this.inner_action.name;
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
            if (_.isString(state.action) && instance.web.client_actions.contains(state.action)) {
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
                        instance.webclient.menu.is_bound.done(function() {
                            if (self.inner_action && self.inner_action.id) {
                                instance.webclient.menu.open_action(self.inner_action.id);
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
        } else if (_.isString(action) && instance.web.client_actions.contains(action)) {
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

        instance.web.bus.trigger('action', action);

        // Ensure context & domain are evaluated and can be manipulated/used
        var ncontext = new instance.web.CompoundContext(options.additional_context, action.context || {});
        action.context = instance.web.pyeval.eval('context', ncontext);
        if (action.context.active_id || action.context.active_ids) {
            // Here we assume that when an `active_id` or `active_ids` is used
            // in the context, we are in a `related` action, so we disable the
            // searchview's default custom filters.
            action.context.search_disable_custom_filters = true;
        }
        if (action.domain) {
            action.domain = instance.web.pyeval.eval(
                'domain', action.domain, action.context || {});
        }

        if (!action.type) {
            console.error("No type for action", action);
            return $.Deferred().reject();
        }
        var type = action.type.replace(/\./g,'_');
        var popup = action.target === 'new';
        var inline = action.target === 'inline' || action.target === 'inlineview';
        action.flags = _.defaults(action.flags || {}, {
            views_switcher : !popup && !inline,
            search_view : !popup && !inline,
            action_buttons : !popup && !inline,
            sidebar : !popup && !inline,
            pager : !popup && !inline,
            display_title : !popup,
            search_disable_custom_filters: action.context && action.context.search_disable_custom_filters
        });
        action.menu_id = options.action_menu_id;
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
            this.dialog = new instance.web.Dialog(this, {
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
            if (widget instanceof instance.web.ViewManager) {
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
            return initialized;
        }
        if (this.inner_widget && this.webclient.has_uncommitted_changes()) {
            return $.Deferred().reject();
        }
        widget = executor.widget();
        this.dialog_stop(executor.action);
        return this.push_widget(widget, executor.action, options.clear_breadcrumbs);
    },
    ir_actions_act_window: function (action, options) {
        var self = this;

        return this.ir_actions_common({
            widget: function () { 
                return new instance.web.ViewManager(self, null, null, null, action); 
            },
            action: action,
            klass: 'oe_act_window',
        }, options);
    },
    ir_actions_client: function (action, options) {
        var self = this;
        var ClientWidget = instance.web.client_actions.get_object(action.tag);
        if (!ClientWidget) {
            return self.do_warn("Action Error", "Could not find client action '" + action.tag + "'.");
        }

        if (!(ClientWidget.prototype instanceof instance.web.Widget)) {
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
        instance.web.blockUI();
        action = _.clone(action);
        var eval_contexts = ([instance.session.user_context] || []).concat([action.context]);
        action.context = instance.web.pyeval.eval('contexts',eval_contexts);

        // iOS devices doesn't allow iframe use the way we do it,
        // opening a new window seems the best way to workaround
        if (navigator.userAgent.match(/(iPod|iPhone|iPad)/)) {
            var params = {
                action: JSON.stringify(action),
                token: new Date().getTime()
            };
            var url = self.session.url('/web/report', params);
            instance.web.unblockUI();
            $('<a href="'+url+'" target="_blank"></a>')[0].click();
            return;
        }
        var c = instance.webclient.crashmanager;
        return $.Deferred(function (d) {
            self.session.get_file({
                url: '/web/report',
                data: {action: JSON.stringify(action)},
                complete: instance.web.unblockUI,
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
            instance.web.redirect(action.url);
        } else {
            window.open(action.url, '_blank');
        }
        return $.when();
    },
});

instance.web.ViewManager =  instance.web.Widget.extend({
    template: "ViewManager",
    /**
     * @param {Object} [dataset] null object (... historical reasons)
     * @param {Array} [views] List of [view_id, view_type]
     * @param {Object} [flags] various boolean describing UI state
     */
    init: function(parent, dataset, views, flags, action) {
        if (action) {
            var flags = action.flags || {};
            if (!('auto_search' in flags)) {
                flags.auto_search = action.auto_search !== false;
            }
            if (action.res_model === 'board.board' && action.view_mode === 'form') {
                action.target = 'inline';
                // Special case for Dashboards
                _.extend(flags, {
                    views_switcher : false,
                    display_title : false,
                    search_view : false,
                    pager : false,
                    sidebar : false,
                    action_buttons : false
                });
            }
            this.action = action;
            this.action_manager = parent;
            var dataset = new instance.web.DataSetSearch(this, action.res_model, action.context, action.domain);
            if (action.res_id) {
                dataset.ids.push(action.res_id);
                dataset.index = 0;
            }
            views = action.views;
        }
        var self = this;
        this._super(parent);

        this.flags = flags || {};
        this.dataset = dataset;
        this.view_order = [];
        this.url_states = {};
        this.views = {};
        this.view_stack = []; // used for breadcrumbs
        this.active_view = null;
        this.searchview = null;
        this.active_search = null;
        this.registry = instance.web.views;
        this.title = this.action && this.action.name;

        _.each(views, function (view) {
            var view_type = view[1] || view.view_type,
                View = instance.web.views.get_object(view_type, true),
                view_label = View ? View.prototype.display_name: (void 'nope'),
                view = {
                    controller: null,
                    options: view.options || {},
                    view_id: view[0] || view.view_id,
                    type: view_type,
                    label: view_label,
                    embedded_view: view.embedded_view,
                    title: self.action && self.action.name,
                    button_label: View ? _.str.sprintf(_t('%(view_type)s view'), {'view_type': (view_label || view_type)}) : (void 'nope'),
                };
            self.view_order.push(view);
            self.views[view_type] = view;
        });
        this.multiple_views = (self.view_order.length - ('form' in this.views ? 1 : 0)) > 1;
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        var self = this;
        var default_view = this.flags.default_view || this.view_order[0].type,
            default_options = this.flags[default_view] && this.flags[default_view].options;

        if (this.flags.headless) {
            this.$('.oe-view-manager-header').hide();
        }
        this._super();
        var $sidebar = this.flags.sidebar ? this.$('.oe-view-manager-sidebar') : undefined,
            $pager = this.$('.oe-view-manager-pager');

        this.$breadcrumbs = this.$('.oe-view-title');
        this.$switch_buttons = this.$('.oe-view-manager-switch button');
        this.$header = this.$('.oe-view-manager-header');
        this.$header_col = this.$header.find('.oe-header-title');
        this.$search_col = this.$header.find('.oe-view-manager-search-view');
        this.$switch_buttons.click(function (event) {
            if (!$(event.target).hasClass('active')) {
                self.switch_mode($(this).data('view-type'));
            }
        });
        var views_ids = {};
        _.each(this.views, function (view) {
            views_ids[view.type] = view.view_id;
            view.options = _.extend({
                $buttons: self.$('.oe-' + view.type + '-buttons'),
                $sidebar : $sidebar,
                $pager : $pager,
                action : self.action,
                action_views_ids : views_ids,
            }, self.flags, self.flags[view.type], view.options);
            if (view.type !== 'form') {
                self.$('.oe-vm-switch-' + view.type).tooltip();
            }
        });
        this.$('.oe_debug_view').click(this.on_debug_changed);
        this.$el.addClass("oe_view_manager_" + ((this.action && this.action.target) || 'current'));

        this.search_view_loaded = this.setup_search_view();
        var main_view_loaded = this.switch_mode(default_view, null, default_options);
            
        return $.when(main_view_loaded, this.search_view_loaded);
    },

    switch_mode: function(view_type, no_store, view_options) {
        var self = this,
            view = this.views[view_type];

        if (!view) {
            return $.Deferred().reject();
        }
        if (view_type !== 'form') {
            this.view_stack = [];
        } 

        this.view_stack.push(view);
        this.active_view = view;
        if (!view.created) {
            view.created = this.create_view.bind(this)(view);
        }
        this.active_search = $.Deferred();

        if (this.searchview
                && this.flags.auto_search
                && view.controller.searchable !== false) {
            $.when(this.search_view_loaded, view.created).done(this.searchview.do_search);
        } else {
            this.active_search.resolve();
        }

        self.update_header();
        return $.when(view.created, this.active_search).done(function () {
            self.active_view = view;
            self._display_view(view.type, view_options);
            self.trigger('switch_mode', view_type, no_store, view_options);
            if (self.session.debug) {
                self.$('.oe_debug_view').html(QWeb.render('ViewManagerDebug', {
                    view: self.active_view.controller,
                    view_manager: self,
                }));
            }
        });
    },
    update_header: function () {
        this.$switch_buttons.removeClass('active');
        this.$('.oe-vm-switch-' + this.active_view.type).addClass('active');
    },
    _display_view: function (view_type, view_options) {
        var self = this;
        this.active_view.$container.show();
        $.when(this.active_view.controller.do_show(view_options)).done(function () { 
            _.each(self.views, function (view) {
                if (view.type !== view_type) {
                    view.controller && view.controller.do_hide();
                    view.$container && view.$container.hide();
                    view.options.$buttons && view.options.$buttons.hide();
                }
            });
            self.active_view.options.$buttons && self.active_view.options.$buttons.show();
            if (self.searchview) {
                var is_hidden = self.active_view.controller.searchable === false;
                self.searchview.toggle_visibility(!is_hidden);
                self.$header_col.toggleClass('col-md-6', !is_hidden).toggleClass('col-md-12', is_hidden);
                self.$search_col.toggle(!is_hidden);
            }
            self.display_breadcrumbs();
        });
    },
    display_breadcrumbs: function () {
        var self = this;
        if (!this.action_manager) return;
        var breadcrumbs = this.action_manager.get_breadcrumbs();
        var $breadcrumbs = _.map(_.initial(breadcrumbs), function (bc) {
            var $link = $('<a>').text(bc.title);
            $link.click(function () {
                self.action_manager.select_widget(bc.view_manager, bc.index);
            });
            return $('<li>').append($link);
        });
        $breadcrumbs.push($('<li>').addClass('active').text(_.last(breadcrumbs).title));
        this.$breadcrumbs
            .empty()
            .append($breadcrumbs);
    },
    create_view: function(view) {
        var self = this,
            View = this.registry.get_object(view.type),
            options = _.clone(view.options),
            view_loaded = $.Deferred();

        if (view.type === "form" && this.action && (this.action.target === 'new' || this.action.target === 'inline')) {
            options.initial_mode = 'edit';
        }
        var controller = new View(this, this.dataset, view.view_id, options),
            $container = this.$(".oe-view-manager-view-" + view.type + ":first");

        $container.hide();
        view.controller = controller;
        view.$container = $container;

        if (view.embedded_view) {
            controller.set_embedded_view(view.embedded_view);
        }
        controller.on('switch_mode', this, this.switch_mode.bind(this));
        controller.on('history_back', this, function () {
            self.action_manager && self.action_manager.trigger('history_back');
        });
        controller.on("change:title", this, function() {
            self.display_breadcrumbs();
        });
        controller.on('view_loaded', this, function () {
            view_loaded.resolve();
        });
        return $.when(controller.appendTo($container), view_loaded)
                .done(function () { 
                    self.trigger("controller_inited", view.type, controller);
                });
    },
    select_view: function (index) {
        var view_type = this.view_stack[index].type;
        this.view_stack.splice(index);
        return this.switch_mode(view_type);
    },
    /**
     * Sets up the current viewmanager's search view.
     *
     * @param {Number|false} view_id the view to use or false for a default one
     * @returns {jQuery.Deferred} search view startup deferred
     */
    setup_search_view: function() {
        if (this.searchview) {
            this.searchview.destroy();
        }

        var view_id = (this.action && this.action.search_view_id && this.action.search_view_id[0]) || false;

        var search_defaults = {};

        var context = this.action ? this.action.context : [];
        _.each(context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });


        var options = {
            hidden: this.flags.search_view === false,
            disable_custom_filters: this.flags.search_disable_custom_filters,
            $buttons: this.$('.oe-search-options'),
        };
        var SearchView = instance.web.SearchView;
        this.searchview = new SearchView(this, this.dataset, view_id, search_defaults, options);

        this.searchview.on('search_data', this, this.search.bind(this));
        return this.searchview.appendTo(this.$(".oe-view-manager-search-view:first"));
    },
    search: function(domains, contexts, groupbys) {
        var self = this,
            controller = this.active_view.controller,
            action_context = this.action.context || {};
        instance.web.pyeval.eval_domains_and_contexts({
            domains: [this.action.domain || []].concat(domains || []),
            contexts: [action_context].concat(contexts || []),
            group_by_seq: groupbys || []
        }).done(function (results) {
            if (results.error) {
                throw new Error(
                        _.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                                      JSON.stringify(results.error)));
            }
            self.dataset._model = new instance.web.Model(
                self.dataset.model, results.context, results.domain);
            var groupby = results.group_by.length
                        ? results.group_by
                        : action_context.group_by;
            if (_.isString(groupby)) {
                groupby = [groupby];
            }
            $.when(controller.do_search(results.domain, results.context, groupby || [])).then(function() {
                self.active_search.resolve();
            });
        });
    },
    do_push_state: function(state) {
        if (this.action_manager) {
            state.view_type = this.active_view.type;
            this.action_manager.do_push_state(state);
        }
    },    
    do_load_state: function(state, warm) {
        var self = this,
            def = this.active_view.created;
        if (state.view_type && state.view_type !== this.active_view.type) {
            def = def.then(function() {
                return self.switch_mode(state.view_type, true);
            });
        } 
        def.done(function() {
            self.active_view.controller.do_load_state(state, warm);
        });
    },
    on_debug_changed: function (evt) {
        var self = this,
            params = $(evt.target).data(),
            val = params.action,
            current_view = this.active_view.controller;
        switch (val) {
            case 'fvg':
                var dialog = new instance.web.Dialog(this, { title: _t("Fields View Get") }).open();
                $('<pre>').text(instance.web.json_node_to_xml(current_view.fields_view.arch, true)).appendTo(dialog.$el);
                break;
            case 'tests':
                this.do_action({
                    name: _t("JS Tests"),
                    target: 'new',
                    type : 'ir.actions.act_url',
                    url: '/web/tests?mod=*'
                });
                break;
            case 'get_metadata':
                var ids = current_view.get_selected_ids();
                if (ids.length === 1) {
                    this.dataset.call('get_metadata', [ids]).done(function(result) {
                        var dialog = new instance.web.Dialog(this, {
                            title: _.str.sprintf(_t("Metadata (%s)"), self.dataset.model),
                            size: 'medium',
                        }, QWeb.render('ViewManagerDebugViewLog', {
                            perm : result[0],
                            format : instance.web.format_value
                        })).open();
                    });
                }
                break;
            case 'toggle_layout_outline':
                current_view.rendering_engine.toggle_layout_debugging();
                break;
            case 'set_defaults':
                current_view.open_defaults_dialog();
                break;
            case 'translate':
                this.do_action({
                    name: _t("Technical Translation"),
                    res_model : 'ir.translation',
                    domain : [['type', '!=', 'object'], '|', ['name', '=', this.dataset.model], ['name', 'ilike', this.dataset.model + ',']],
                    views: [[false, 'list'], [false, 'form']],
                    type : 'ir.actions.act_window',
                    view_type : "list",
                    view_mode : "list"
                });
                break;
            case 'fields':
                this.dataset.call('fields_get', [false, {}]).done(function (fields) {
                    var $root = $('<dl>');
                    _(fields).each(function (attributes, name) {
                        $root.append($('<dt>').append($('<h4>').text(name)));
                        var $attrs = $('<dl>').appendTo($('<dd>').appendTo($root));
                        _(attributes).each(function (def, name) {
                            if (def instanceof Object) {
                                def = JSON.stringify(def);
                            }
                            $attrs
                                .append($('<dt>').text(name))
                                .append($('<dd style="white-space: pre-wrap;">').text(def));
                        });
                    });
                    new instance.web.Dialog(self, {
                        title: _.str.sprintf(_t("Model %s fields"),
                                             self.dataset.model),
                        }, $root).open();
                });
                break;
            case 'edit_workflow':
                return this.do_action({
                    res_model : 'workflow',
                    name: _t('Edit Workflow'),
                    domain : [['osv', '=', this.dataset.model]],
                    views: [[false, 'list'], [false, 'form'], [false, 'diagram']],
                    type : 'ir.actions.act_window',
                    view_type : 'list',
                    view_mode : 'list'
                });
            case 'edit':
                this.do_edit_resource(params.model, params.id, evt.target.text);
                break;
            case 'manage_filters':
                this.do_action({
                    res_model: 'ir.filters',
                    name: _t('Manage Filters'),
                    views: [[false, 'list'], [false, 'form']],
                    type: 'ir.actions.act_window',
                    context: {
                        search_default_my_filters: true,
                        search_default_model_id: this.dataset.model
                    }
                });
                break;
            case 'print_workflow':
                if (current_view.get_selected_ids  && current_view.get_selected_ids().length == 1) {
                    instance.web.blockUI();
                    var action = {
                        context: { active_ids: current_view.get_selected_ids() },
                        report_name: "workflow.instance.graph",
                        datas: {
                            model: this.dataset.model,
                            id: current_view.get_selected_ids()[0],
                            nested: true,
                        }
                    };
                    this.session.get_file({
                        url: '/web/report',
                        data: {action: JSON.stringify(action)},
                        complete: instance.web.unblockUI
                    });
                }
                break;
            case 'leave_debug':
                window.location.search="?";
                break;
            default:
                if (val) {
                    console.warn("No debug handler for ", val);
                }
        }
    },
    do_edit_resource: function(model, id, name) {
        this.do_action({
            res_model : model,
            res_id : id,
            name: name,
            type : 'ir.actions.act_window',
            view_type : 'form',
            view_mode : 'form',
            views : [[false, 'form']],
            target : 'new',
            flags : {
                action_buttons : true,
                headless: true,
            }
        });
    },
});

instance.web.Sidebar = instance.web.Widget.extend({
    init: function(parent) {
        var self = this;
        this._super(parent);
        var view = this.getParent();
        this.sections = [
            { 'name' : 'print', 'label' : _t('Print'), },
            { 'name' : 'other', 'label' : _t('More'), }
        ];
        this.items = {
            'print' : [],
            'other' : []
        };
        this.fileupload_id = _.uniqueId('oe_fileupload');
        $(window).on(this.fileupload_id, function() {
            var args = [].slice.call(arguments).slice(1);
            self.do_attachement_update(self.dataset, self.model_id,args);
            instance.web.unblockUI();
        });
    },
    start: function() {
        var self = this;
        this._super(this);
        this.redraw();
        this.$el.on('click','.dropdown-menu li a', function(event) {
            var section = $(this).data('section');
            var index = $(this).data('index');
            var item = self.items[section][index];
            if (item.callback) {
                item.callback.apply(self, [item]);
            } else if (item.action) {
                self.on_item_action_clicked(item);
            } else if (item.url) {
                return true;
            }
            event.preventDefault();
        });
    },
    redraw: function() {
        var self = this;
        self.$el.html(QWeb.render('Sidebar', {widget: self}));

        // Hides Sidebar sections when item list is empty
        this.$('.oe_form_dropdown_section').each(function() {
            $(this).toggle(!!$(this).find('li').length);
        });
        self.$("[title]").tooltip({
            delay: { show: 500, hide: 0}
        });
    },
    /**
     * For each item added to the section:
     *
     * ``label``
     *     will be used as the item's name in the sidebar, can be html
     *
     * ``action``
     *     descriptor for the action which will be executed, ``action`` and
     *     ``callback`` should be exclusive
     *
     * ``callback``
     *     function to call when the item is clicked in the sidebar, called
     *     with the item descriptor as its first argument (so information
     *     can be stored as additional keys on the object passed to
     *     ``add_items``)
     *
     * ``classname`` (optional)
     *     ``@class`` set on the sidebar serialization of the item
     *
     * ``title`` (optional)
     *     will be set as the item's ``@title`` (tooltip)
     *
     * @param {String} section_code
     * @param {Array<{label, action | callback[, classname][, title]}>} items
     */
    add_items: function(section_code, items) {
        var self = this;
        if (items) {
            this.items[section_code].unshift.apply(this.items[section_code],items);
            this.redraw();
        }
    },
    add_toolbar: function(toolbar) {
        var self = this;
        _.each(['print','action','relate'], function(type) {
            var items = toolbar[type];
            if (items) {
                for (var i = 0; i < items.length; i++) {
                    items[i] = {
                        label: items[i]['name'],
                        action: items[i],
                        classname: 'oe_sidebar_' + type
                    };
                }
                self.add_items(type=='print' ? 'print' : 'other', items);
            }
        });
    },
    on_item_action_clicked: function(item) {
        var self = this;
        self.getParent().sidebar_eval_context().done(function (sidebar_eval_context) {
            var ids = self.getParent().get_selected_ids();
            var domain;
            if (self.getParent().get_active_domain) {
                domain = self.getParent().get_active_domain();
            }
            else {
                domain = $.Deferred().resolve(undefined);
            }
            if (ids.length === 0) {
                new instance.web.Dialog(this, { title: _t("Warning"), size: 'medium',}, $("<div />").text(_t("You must choose at least one record."))).open();
                return false;
            }
            var active_ids_context = {
                active_id: ids[0],
                active_ids: ids,
                active_model: self.getParent().dataset.model,
            };

            $.when(domain).done(function (domain) {
                if (domain !== undefined) {
                    active_ids_context.active_domain = domain;
                }
                var c = instance.web.pyeval.eval('context',
                new instance.web.CompoundContext(
                    sidebar_eval_context, active_ids_context));

                self.rpc("/web/action/load", {
                    action_id: item.action.id,
                    context: c
                }).done(function(result) {
                    result.context = new instance.web.CompoundContext(
                        result.context || {}, active_ids_context)
                            .set_eval_context(c);
                    result.flags = result.flags || {};
                    result.flags.new_window = true;
                    self.do_action(result, {
                        on_close: function() {
                            // reload view
                            self.getParent().reload();
                        },
                    });
                });
            });
        });
    },
    do_attachement_update: function(dataset, model_id, args) {
        var self = this;
        this.dataset = dataset;
        this.model_id = model_id;
        if (args && args[0].error) {
            this.do_warn(_t('Uploading Error'), args[0].error);
        }
        if (!model_id) {
            this.on_attachments_loaded([]);
        } else {
            var dom = [ ['res_model', '=', dataset.model], ['res_id', '=', model_id], ['type', 'in', ['binary', 'url']] ];
            var ds = new instance.web.DataSetSearch(this, 'ir.attachment', dataset.get_context(), dom);
            ds.read_slice(['name', 'url', 'type', 'create_uid', 'create_date', 'write_uid', 'write_date'], {}).done(this.on_attachments_loaded);
        }
    },
    on_attachments_loaded: function(attachments) {
        var self = this;
        var items = [];
        var prefix = this.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'name'});
        _.each(attachments,function(a) {
            a.label = a.name;
            if(a.type === "binary") {
                a.url = prefix  + '&id=' + a.id + '&t=' + (new Date().getTime());
            }
        });
        self.items.files = attachments;
        self.redraw();
        this.$('.oe_sidebar_add_attachment .oe_form_binary_file').change(this.on_attachment_changed);
        this.$el.find('.oe_sidebar_delete_item').click(this.on_attachment_delete);
    },
    on_attachment_changed: function(e) {
        var $e = $(e.target);
        if ($e.val() !== '') {
            this.$el.find('form.oe_form_binary_form').submit();
            $e.parent().find('input[type=file]').prop('disabled', true);
            $e.parent().find('button').prop('disabled', true).find('img, span').toggle();
            this.$('.oe_sidebar_add_attachment a').text(_t('Uploading...'));
            instance.web.blockUI();
        }
    },
    on_attachment_delete: function(e) {
        e.preventDefault();
        e.stopPropagation();
        var self = this;
        var $e = $(e.currentTarget);
        if (confirm(_t("Do you really want to delete this attachment ?"))) {
            (new instance.web.DataSet(this, 'ir.attachment')).unlink([parseInt($e.attr('data-id'), 10)]).done(function() {
                self.do_attachement_update(self.dataset, self.model_id);
            });
        }
    }
});

instance.web.View = instance.web.Widget.extend({
    // name displayed in view switchers
    display_name: '',
    /**
     * Define a view type for each view to allow automatic call to fields_view_get.
     */
    view_type: undefined,
    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.ViewManager = parent;
        this.dataset = dataset;
        this.view_id = view_id;
        this.set_default_options(options);
    },
    start: function () {
        return this.load_view();
    },
    load_view: function(context) {
        var self = this;
        var view_loaded_def;
        if (this.embedded_view) {
            view_loaded_def = $.Deferred();
            $.async_when().done(function() {
                view_loaded_def.resolve(self.embedded_view);
            });
        } else {
            if (! this.view_type)
                console.warn("view_type is not defined", this);
            view_loaded_def = instance.web.fields_view_get({
                "model": this.dataset._model,
                "view_id": this.view_id,
                "view_type": this.view_type,
                "toolbar": !!this.options.$sidebar,
                "context": this.dataset.get_context(),
            });
        }
        return this.alive(view_loaded_def).then(function(r) {
            self.fields_view = r;
            // add css classes that reflect the (absence of) access rights
            self.$el.addClass('oe_view')
                .toggleClass('oe_cannot_create', !self.is_action_enabled('create'))
                .toggleClass('oe_cannot_edit', !self.is_action_enabled('edit'))
                .toggleClass('oe_cannot_delete', !self.is_action_enabled('delete'));
            return $.when(self.view_loading(r)).then(function() {
                self.trigger('view_loaded', r);
            });
        });
    },
    view_loading: function(r) {
    },
    set_default_options: function(options) {
        this.options = options || {};
        _.defaults(this.options, {
            // All possible views options should be defaulted here
            $sidebar: null,
            sidebar_id: null,
            action: null,
            action_views_ids: {}
        });
    },
    /**
     * Fetches and executes the action identified by ``action_data``.
     *
     * @param {Object} action_data the action descriptor data
     * @param {String} action_data.name the action name, used to uniquely identify the action to find and execute it
     * @param {String} [action_data.special=null] special action handlers (currently: only ``'cancel'``)
     * @param {String} [action_data.type='workflow'] the action type, if present, one of ``'object'``, ``'action'`` or ``'workflow'``
     * @param {Object} [action_data.context=null] additional action context, to add to the current context
     * @param {instance.web.DataSet} dataset a dataset object used to communicate with the server
     * @param {Object} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_closed callback to execute when dialog is closed or when the action does not generate any result (no new action)
     */
    do_execute_action: function (action_data, dataset, record_id, on_closed) {
        var self = this;
        var result_handler = function () {
            if (on_closed) { on_closed.apply(null, arguments); }
            if (self.getParent() && self.getParent().on_action_executed) {
                return self.getParent().on_action_executed.apply(null, arguments);
            }
        };
        var context = new instance.web.CompoundContext(dataset.get_context(), action_data.context || {});

        // response handler
        var handler = function (action) {
            if (action && action.constructor == Object) {
                // filter out context keys that are specific to the current action.
                // Wrong default_* and search_default_* values will no give the expected result
                // Wrong group_by values will simply fail and forbid rendering of the destination view
                var ncontext = new instance.web.CompoundContext(
                    _.object(_.reject(_.pairs(dataset.get_context().eval()), function(pair) {
                      return pair[0].match('^(?:(?:default_|search_default_).+|.+_view_ref|group_by|group_by_no_leaf|active_id|active_ids)$') !== null;
                    }))
                );
                ncontext.add(action_data.context || {});
                ncontext.add({active_model: dataset.model});
                if (record_id) {
                    ncontext.add({
                        active_id: record_id,
                        active_ids: [record_id],
                    });
                }
                ncontext.add(action.context || {});
                action.context = ncontext;
                return self.do_action(action, {
                    on_close: result_handler,
                });
            } else {
                self.do_action({"type":"ir.actions.act_window_close"});
                return result_handler();
            }
        };

        if (action_data.special === 'cancel') {
            return handler({"type":"ir.actions.act_window_close"});
        } else if (action_data.type=="object") {
            var args = [[record_id]];
            if (action_data.args) {
                try {
                    // Warning: quotes and double quotes problem due to json and xml clash
                    // Maybe we should force escaping in xml or do a better parse of the args array
                    var additional_args = JSON.parse(action_data.args.replace(/'/g, '"'));
                    args = args.concat(additional_args);
                } catch(e) {
                    console.error("Could not JSON.parse arguments", action_data.args);
                }
            }
            args.push(context);
            return dataset.call_button(action_data.name, args).then(handler).then(function () {
                if (instance.webclient) {
                    instance.webclient.menu.do_reload_needaction();
                }
            });
        } else if (action_data.type=="action") {
            return this.rpc('/web/action/load', {
                action_id: action_data.name,
                context: _.extend(instance.web.pyeval.eval('context', context), {'active_model': dataset.model, 'active_ids': dataset.ids, 'active_id': record_id}),
                do_not_eval: true
            }).then(handler);
        } else  {
            return dataset.exec_workflow(record_id, action_data.name).then(handler);
        }
    },
    /**
     * Directly set a view to use instead of calling fields_view_get. This method must
     * be called before start(). When an embedded view is set, underlying implementations
     * of instance.web.View must use the provided view instead of any other one.
     *
     * @param embedded_view A view.
     */
    set_embedded_view: function(embedded_view) {
        this.embedded_view = embedded_view;
    },
    do_show: function () {
        this.$el.show();
        instance.web.bus.trigger('view_shown', this);
    },
    do_hide: function () {
        this.$el.hide();
    },
    is_active: function () {
        return this.ViewManager.active_view.controller === this;
    }, /**
     * Wraps fn to only call it if the current view is the active one. If the
     * current view is not active, doesn't call fn.
     *
     * fn can not return anything, as a non-call to fn can't return anything
     * either
     *
     * @param {Function} fn function to wrap in the active guard
     */
    guard_active: function (fn) {
        var self = this;
        return function () {
            if (self.is_active()) {
                fn.apply(self, arguments);
            }
        };
    },
    do_push_state: function(state) {
        if (this.getParent() && this.getParent().do_push_state) {
            this.getParent().do_push_state(state);
        }
    },
    do_load_state: function (state, warm) {

    },
    /**
     * Switches to a specific view type
     */
    do_switch_view: function() {
        this.trigger.apply(this, ['switch_mode'].concat(_.toArray(arguments)));
    },
    do_search: function(domain, context, group_by) {
    },
    on_sidebar_export: function() {
        new instance.web.DataExport(this, this.dataset).open();
    },
    sidebar_eval_context: function () {
        return $.when({});
    },
    /**
     * Asks the view to reload itself, if the reloading is asynchronous should
     * return a {$.Deferred} indicating when the reloading is done.
     */
    reload: function () {
        return $.when();
    },
    /**
     * Return whether the user can perform the action ('create', 'edit', 'delete') in this view.
     * An action is disabled by setting the corresponding attribute in the view's main element,
     * like: <form string="" create="false" edit="false" delete="false">
     */
    is_action_enabled: function(action) {
        var attrs = this.fields_view.arch.attrs;
        return (action in attrs) ? JSON.parse(attrs[action]) : true;
    },
});

/**
 * Performs a fields_view_get and apply postprocessing.
 * return a {$.Deferred} resolved with the fvg
 *
 * @param {Object} args
 * @param {String|Object} args.model instance.web.Model instance or string repr of the model
 * @param {Object} [args.context] context if args.model is a string
 * @param {Number} [args.view_id] id of the view to be loaded, default view if null
 * @param {String} [args.view_type] type of view to be loaded if view_id is null
 * @param {Boolean} [args.toolbar=false] get the toolbar definition
 */
instance.web.fields_view_get = function(args) {
    function postprocess(fvg) {
        var doc = $.parseXML(fvg.arch).documentElement;
        fvg.arch = instance.web.xml_to_json(doc, (doc.nodeName.toLowerCase() !== 'kanban'));
        if ('id' in fvg.fields) {
            // Special case for id's
            var id_field = fvg.fields['id'];
            id_field.original_type = id_field.type;
            id_field.type = 'id';
        }
        _.each(fvg.fields, function(field) {
            _.each(field.views || {}, function(view) {
                postprocess(view);
            });
        });
        return fvg;
    }
    args = _.defaults(args, {
        toolbar: false,
    });
    var model = args.model;
    if (typeof model === 'string') {
        model = new instance.web.Model(args.model, args.context);
    }
    return args.model.call('fields_view_get', {
        view_id: args.view_id,
        view_type: args.view_type,
        context: args.context,
        toolbar: args.toolbar
    }).then(function(fvg) {
        return postprocess(fvg);
    });
};

instance.web.xml_to_json = function(node, strip_whitespace) {
    switch (node.nodeType) {
        case 9:
            return instance.web.xml_to_json(node.documentElement, strip_whitespace);
        case 3:
        case 4:
            return (strip_whitespace && node.data.trim() === '') ? undefined : node.data;
        case 1:
            var attrs = $(node).getAttributes();
            _.each(['domain', 'filter_domain', 'context', 'default_get'], function(key) {
                if (attrs[key]) {
                    try {
                        attrs[key] = JSON.parse(attrs[key]);
                    } catch(e) { }
                }
            });
            return {
                tag: node.tagName.toLowerCase(),
                attrs: attrs,
                children: _.compact(_.map(node.childNodes, function(node) {
                    return instance.web.xml_to_json(node, strip_whitespace);
                })),
            };
    }
};

instance.web.json_node_to_xml = function(node, human_readable, indent) {
    // For debugging purpose, this function will convert a json node back to xml
    indent = indent || 0;
    var sindent = (human_readable ? (new Array(indent + 1).join('\t')) : ''),
        r = sindent + '<' + node.tag,
        cr = human_readable ? '\n' : '';

    if (typeof(node) === 'string') {
        return sindent + node;
    } else if (typeof(node.tag) !== 'string' || !node.children instanceof Array || !node.attrs instanceof Object) {
        throw new Error(
            _.str.sprintf(_t("Node [%s] is not a JSONified XML node"),
                          JSON.stringify(node)));
    }
    for (var attr in node.attrs) {
        var vattr = node.attrs[attr];
        if (typeof(vattr) !== 'string') {
            // domains, ...
            vattr = JSON.stringify(vattr);
        }
        vattr = vattr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        if (human_readable) {
            vattr = vattr.replace(/&quot;/g, "'");
        }
        r += ' ' + attr + '="' + vattr + '"';
    }
    if (node.children && node.children.length) {
        r += '>' + cr;
        var childs = [];
        for (var i = 0, ii = node.children.length; i < ii; i++) {
            childs.push(instance.web.json_node_to_xml(node.children[i], human_readable, indent + 1));
        }
        r += childs.join(cr);
        r += cr + sindent + '</' + node.tag + '>';
        return r;
    } else {
        return r + '/>';
    }
};
instance.web.xml_to_str = function(node) {
    var str = "";
    if (window.XMLSerializer) {
        str = (new XMLSerializer()).serializeToString(node);
    } else if (window.ActiveXObject) {
        str = node.xml;
    } else {
        throw new Error(_t("Could not serialize XML"));
    }
    // Browsers won't deal with self closing tags except void elements:
    // http://www.w3.org/TR/html-markup/syntax.html
    var void_elements = 'area base br col command embed hr img input keygen link meta param source track wbr'.split(' ');

    // The following regex is a bit naive but it's ok for the xmlserializer output
    str = str.replace(/<([a-z]+)([^<>]*)\s*\/\s*>/g, function(match, tag, attrs) {
        if (void_elements.indexOf(tag) < 0) {
            return "<" + tag + attrs + "></" + tag + ">";
        } else {
            return match;
        }
    });
    return str;
};

/**
 * Registry for all the main views
 */
instance.web.views = new instance.web.Registry();

})();

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
