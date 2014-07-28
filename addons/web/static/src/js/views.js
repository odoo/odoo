/*---------------------------------------------------------
 * OpenERP web library
 *---------------------------------------------------------*/

openerp.web.views = function(session) {
var QWeb = session.web.qweb,
    _t = session.web._t;

/**
 * Registry for all the client actions key: tag value: widget
 */
session.web.client_actions = new session.web.Registry();

/**
 * Registry for all the main views
 */
session.web.views = new session.web.Registry();

session.web.ActionManager = session.web.OldWidget.extend({
    init: function(parent) {
        this._super(parent);
        this.inner_action = null;
        this.inner_viewmanager = null;
        this.dialog = null;
        this.dialog_viewmanager = null;
        this.client_widget = null;
    },
    render: function() {
        return '<div id="' + this.element_id + '" style="height: 100%;"></div>';
    },
    dialog_stop: function () {
        if (this.dialog) {
            this.dialog_viewmanager.stop();
            this.dialog_viewmanager = null;
            this.dialog.stop();
            this.dialog = null;
        }
    },
    content_stop: function () {
        if (this.inner_viewmanager) {
            this.inner_viewmanager.stop();
            this.inner_viewmanager = null;
        }
        if (this.client_widget) {
            this.client_widget.stop();
            this.client_widget = null;
        }
    },
    do_push_state: function(state) {
        if (this.widget_parent && this.widget_parent.do_push_state) {
            if (this.inner_action) {
                state['title'] = this.inner_action.name;
                state['model'] = this.inner_action.res_model;
                if (this.inner_action.id) {
                    state['action_id'] = this.inner_action.id;
                }
            }
            this.widget_parent.do_push_state(state);
        }
    },
    do_load_state: function(state, warm) {
        var self = this,
            action_loaded;
        if (state.action_id) {
            var run_action = (!this.inner_viewmanager) || this.inner_viewmanager.action.id !== state.action_id;
            if (run_action) {
                this.null_action();
                action_loaded = this.do_action(state.action_id);
            }
        } else if (state.model && state.id) {
            // TODO handle context & domain ?
            this.null_action();
            var action = {
                res_model: state.model,
                res_id: state.id,
                type: 'ir.actions.act_window',
                views: [[false, 'page'], [false, 'form']]
            };
            action_loaded = this.do_action(action);
        } else if (state.sa) {
            // load session action
            var self = this;
            this.null_action();
            action_loaded = this.rpc('/web/session/get_session_action',  {key: state.sa}).pipe(function(action) {
                if (action) {
                    return self.do_action(action);
                }
            });
        } else if (state.client_action) {
            this.null_action();
            this.ir_actions_client(state.client_action);
        }

        $.when(action_loaded || null).then(function() {
            if (self.inner_viewmanager) {
                self.inner_viewmanager.do_load_state(state, warm);
            }
        });
    },
    do_action: function(action, on_close) {
        if (_.isNumber(action)) {
            var self = this;
            return self.rpc("/web/action/load", { action_id: action }, function(result) {
                self.do_action(result.result, on_close);
            });
        }
        if (!action.type) {
            console.error("No type for action", action);
            return;
        }
        var type = action.type.replace(/\./g,'_');
        var popup = action.target === 'new';
        action.flags = _.extend({
            views_switcher : !popup,
            search_view : !popup,
            action_buttons : !popup,
            sidebar : !popup,
            pager : !popup,
            display_title : !popup
        }, action.flags || {});
        if (!(type in this)) {
            console.error("Action manager can't handle action of type " + action.type, action);
            return;
        }
        return this[type](action, on_close);
    },
    null_action: function() {
        this.dialog_stop();
        this.content_stop();
    },
    ir_actions_act_window: function (action, on_close) {
        var self = this;
        if (_(['base.module.upgrade', 'base.setup.installer'])
                .contains(action.res_model)) {
            var old_close = on_close;
            on_close = function () {
                session.webclient.do_reload().then(old_close);
            };
        }
        if (action.target === 'new') {
            if (this.dialog == null) {
                this.dialog = new session.web.Dialog(this, { width: '80%' });
                if(on_close)
                    this.dialog.on_close.add(on_close);
            } else {
                this.dialog_viewmanager.stop();
            }
            this.dialog.dialog_title = action.name;
            this.dialog_viewmanager = new session.web.ViewManagerAction(this, action);
            this.dialog_viewmanager.appendTo(this.dialog.$element);
            this.dialog.open();
        } else  {
            if(action.menu_id) {
                return this.widget_parent.do_action(action, function () {
                    session.webclient.menu.open_menu(action.menu_id);
                });
            }
            this.dialog_stop();
            this.content_stop();
            this.inner_action = action;
            this.inner_viewmanager = new session.web.ViewManagerAction(this, action);
            this.inner_viewmanager.appendTo(this.$element);
        }
    },
    ir_actions_act_window_close: function (action, on_closed) {
        if (!this.dialog && on_closed) {
            on_closed();
        }
        this.dialog_stop();
    },
    ir_actions_server: function (action, on_closed) {
        var self = this;
        this.rpc('/web/action/run', {
            action_id: action.id,
            context: action.context || {}
        }).then(function (action) {
            self.do_action(action, on_closed)
        });
    },
    ir_actions_client: function (action) {
        this.content_stop();
        this.dialog_stop();
        var ClientWidget = session.web.client_actions.get_object(action.tag);
        (this.client_widget = new ClientWidget(this, action.params)).appendTo(this);
    },
    ir_actions_report_xml: function(action, on_closed) {
        var self = this;
        $.blockUI();
        self.rpc("/web/session/eval_domain_and_context", {
            contexts: [action.context],
            domains: []
        }).then(function(res) {
            action = _.clone(action);
            action.context = res.context;
            self.session.get_file({
                url: '/web/report',
                data: {action: JSON.stringify(action)},
                complete: $.unblockUI,
                success: function(){
                    if (!self.dialog && on_closed) {
                        on_closed();
                    }
                    self.dialog_stop();
                },
                error: session.webclient.crashmanager.on_rpc_error
            })
        });
    },
    ir_actions_act_url: function (action) {
        window.open(action.url, action.target === 'self' ? '_self' : '_blank');
    },
    ir_ui_menu: function (action) {
        this.widget_parent.do_action(action);
    }
});

session.web.ViewManager =  session.web.OldWidget.extend(/** @lends session.web.ViewManager# */{
    template: "ViewManager",
    /**
     * @constructs session.web.ViewManager
     * @extends session.web.OldWidget
     *
     * @param parent
     * @param dataset
     * @param views
     */
    init: function(parent, dataset, views, flags) {
        this._super(parent);
        this.model = dataset ? dataset.model : undefined;
        this.dataset = dataset;
        this.searchview = null;
        this.active_view = null;
        this.views_src = _.map(views, function(x) {
            if (x instanceof Array) {
                var View = session.web.views.get_object(x[1], true);
                return {
                    view_id: x[0],
                    view_type: x[1],
                    label: View ? View.prototype.display_name : (void 'nope')
                };
            } else {
                return x;
            }
        });
        this.views = {};
        this.flags = flags || {};
        this.registry = session.web.views;
        this.views_history = [];
    },
    render: function() {
        return session.web.qweb.render(this.template, {
            self: this,
            prefix: this.element_id,
            views: this.views_src});
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        this._super();
        var self = this;
        this.$element.find('.oe_vm_switch button').click(function() {
            self.on_mode_switch($(this).data('view-type'));
        });
        var views_ids = {};
        _.each(this.views_src, function(view) {
            self.views[view.view_type] = $.extend({}, view, {
                deferred : $.Deferred(),
                controller : null,
                options : _.extend({
                    sidebar_id : self.element_id + '_sidebar_' + view.view_type,
                    action : self.action,
                    action_views_ids : views_ids
                }, self.flags, self.flags[view.view_type] || {}, view.options || {})
            });
            views_ids[view.view_type] = view.view_id;
        });
        if (this.flags.views_switcher === false) {
            this.$element.find('.oe_vm_switch').hide();
        }
        // If no default view defined, switch to the first one in sequence
        var default_view = this.flags.default_view || this.views_src[0].view_type;
        return this.on_mode_switch(default_view);
    },
    /**
     * Asks the view manager to switch visualization mode.
     *
     * @param {String} view_type type of view to display
     * @param {Boolean} [no_store=false] don't store the view being switched to on the switch stack
     * @returns {jQuery.Deferred} new view loading promise
     */
    on_mode_switch: function(view_type, no_store) {
        var self = this,
            view = this.views[view_type],
            view_promise;
        if(!view)
            return $.Deferred().reject();

        if (!no_store) {
            this.views_history.push(view_type);
        }
        this.active_view = view_type;

        if (!view.controller) {
            // Lazy loading of views
            var controllerclass = this.registry.get_object(view_type);
            var controller = new controllerclass(this, this.dataset, view.view_id, view.options);
            if (view.embedded_view) {
                controller.set_embedded_view(view.embedded_view);
            }
            controller.do_switch_view.add_last(this.on_mode_switch);
            controller.do_prev_view.add_last(this.on_prev_view);
            var container = $("#" + this.element_id + '_view_' + view_type);
            view_promise = controller.appendTo(container);
            this.views[view_type].controller = controller;
            $.when(view_promise).then(function() {
                self.views[view_type].deferred.resolve(view_type);
                self.on_controller_inited(view_type, controller);
                if (self.searchview
                        && self.flags.auto_search
                        && view.controller.searchable !== false) {
                    self.searchview.ready.then(self.searchview.do_search);
                }
            });
        } else if (this.searchview
                && self.flags.auto_search
                && view.controller.searchable !== false) {
            this.searchview.ready.then(this.searchview.do_search);
        }

        if (this.searchview) {
            this.searchview[(view.controller.searchable === false || this.searchview.hidden) ? 'hide' : 'show']();
        }

        this.$element
            .find('.oe_vm_switch button').removeAttr('disabled')
            .filter('[data-view-type="' + view_type + '"]')
            .attr('disabled', true);

        $.when(view_promise).then(function () {
            _.each(_.keys(self.views), function(view_name) {
                var controller = self.views[view_name].controller;
                if (controller) {
                    if (view_name === view_type) {
                        controller.do_show();
                    } else {
                        controller.do_hide();
                    }
                }
            });

            self.$element.find('.oe_view_title_text:first').text(
                    self.display_title());
        });
        return view_promise;
    },
    /**
     * Returns to the view preceding the caller view in this manager's
     * navigation history (the navigation history is appended to via
     * on_mode_switch)
     *
     * @param {Object} [options]
     * @param {Boolean} [options.created=false] resource was created
     * @param {String} [options.default=null] view to switch to if no previous view
     * @returns {$.Deferred} switching end signal
     */
    on_prev_view: function (options) {
        options = options || {};
        var current_view = this.views_history.pop();
        var previous_view = this.views_history[this.views_history.length - 1] || options['default'];
        if (options.created && current_view === 'form' && previous_view === 'list') {
            // APR special case: "If creation mode from list (and only from a list),
            // after saving, go to page view (don't come back in list)"
            return this.on_mode_switch('page');
        } else if (options.created && !previous_view && this.action && this.action.flags.default_view === 'form') {
            // APR special case: "If creation from dashboard, we have no previous view
            return this.on_mode_switch('page');
        }
        return this.on_mode_switch(previous_view, true);
    },
    /**
     * Sets up the current viewmanager's search view.
     *
     * @param {Number|false} view_id the view to use or false for a default one
     * @returns {jQuery.Deferred} search view startup deferred
     */
    setup_search_view: function(view_id, search_defaults) {
        var self = this;
        if (this.searchview) {
            this.searchview.stop();
        }
        this.searchview = new session.web.SearchView(
                this, this.dataset,
                view_id, search_defaults, this.flags.search_view === false);

        this.searchview.on_search.add(this.do_searchview_search);
        return this.searchview.appendTo($("#" + this.element_id + "_search"));
    },
    do_searchview_search: function(domains, contexts, groupbys) {
        var self = this,
            controller = this.views[this.active_view].controller,
            action_context = this.action.context || {};
        this.rpc('/web/session/eval_domain_and_context', {
            domains: [this.action.domain || []].concat(domains || []),
            contexts: [action_context].concat(contexts || []),
            group_by_seq: groupbys || []
        }, function (results) {
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            var groupby = results.group_by.length
                        ? results.group_by
                        : action_context.group_by;
            if (_.isString(groupby)) {
                groupby = [groupby];
            }
            controller.do_search(results.domain, results.context, groupby || []);
        });
    },
    /**
     * Event launched when a controller has been inited.
     *
     * @param {String} view_type type of view
     * @param {String} view the inited controller
     */
    on_controller_inited: function(view_type, view) {
    },
    /**
     * Called when one of the view want to execute an action
     */
    on_action: function(action) {
    },
    on_create: function() {
    },
    on_remove: function() {
    },
    on_edit: function() {
    },
    /**
     * Called by children view after executing an action
     */
    on_action_executed: function () {
    },
    display_title: function () {
        var view = this.views[this.active_view];
        if (view) {
            // ick
            return view.controller.fields_view.arch.attrs.string;
        }
        return '';
    }
});

session.web.ViewManagerAction = session.web.ViewManager.extend(/** @lends oepnerp.web.ViewManagerAction# */{
    template:"ViewManagerAction",
    /**
     * @constructs session.web.ViewManagerAction
     * @extends session.web.ViewManager
     *
     * @param {session.web.ActionManager} parent parent object/widget
     * @param {Object} action descriptor for the action this viewmanager needs to manage its views.
     */
    init: function(parent, action) {
        // dataset initialization will take the session from ``this``, so if we
        // do not have it yet (and we don't, because we've not called our own
        // ``_super()``) rpc requests will blow up.
        var flags = action.flags || {};
        if (!('auto_search' in flags)) {
            flags.auto_search = action.auto_search !== false;
        }
        if (action.res_model == 'board.board' && action.view_mode === 'form') {
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
        this._super(parent, null, action.views, flags);
        this.session = parent.session;
        this.action = action;
        var dataset = new session.web.DataSetSearch(this, action.res_model, action.context, action.domain);
        if (action.res_id) {
            dataset.ids.push(action.res_id);
            dataset.index = 0;
        }
        this.dataset = dataset;

        // setup storage for session-wise menu hiding
        if (this.session.hidden_menutips) {
            return;
        }
        this.session.hidden_menutips = {}
    },
    /**
     * Initializes the ViewManagerAction: sets up the searchview (if the
     * searchview is enabled in the manager's action flags), calls into the
     * parent to initialize the primary view and (if the VMA has a searchview)
     * launches an initial search after both views are done rendering.
     */
    start: function() {
        var self = this,
            searchview_loaded,
            search_defaults = {};
        _.each(this.action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });
        // init search view
        var searchview_id = this.action['search_view_id'] && this.action['search_view_id'][0];

        searchview_loaded = this.setup_search_view(searchview_id || false, search_defaults);

        var main_view_loaded = this._super();

        var manager_ready = $.when(searchview_loaded, main_view_loaded);

        this.$element.find('.oe_debug_view').change(this.on_debug_changed);

        if (this.action.help && !this.flags.low_profile) {
            var Users = new session.web.DataSet(self, 'res.users'),
                $tips = this.$element.find('.oe_view_manager_menu_tips');
            $tips.delegate('blockquote button', 'click', function() {
                var $this = $(this);
                //noinspection FallthroughInSwitchStatementJS
                switch ($this.attr('name')) {
                case 'disable':
                    Users.write(self.session.uid, {menu_tips:false});
                case 'hide':
                    $this.closest('blockquote').hide();
                    self.session.hidden_menutips[self.action.id] = true;
                }
            });
            if (!(self.action.id in self.session.hidden_menutips)) {
                Users.read_ids([this.session.uid], ['menu_tips']).then(function(users) {
                    var user = users[0];
                    if (!(user && user.id === self.session.uid)) {
                        return;
                    }
                    $tips.find('blockquote').toggle(user.menu_tips);
                });
            }
        }

        var $res_logs = this.$element.find('.oe-view-manager-logs:first');
        $res_logs.delegate('a.oe-more-logs', 'click', function () {
            $res_logs.removeClass('oe-folded');
            return false;
        }).delegate('a.oe-remove-everything', 'click', function () {
            $res_logs.removeClass('oe-has-more').find('ul').empty();
            $res_logs.css('display','none');
            return false;
        });
        $res_logs.css('display','none');

        return manager_ready;
    },
    on_debug_changed: function (evt) {
        var self = this,
            $sel = $(evt.currentTarget),
            $option = $sel.find('option:selected'),
            val = $sel.val(),
            current_view = this.views[this.active_view].controller;
        switch (val) {
            case 'fvg':
                var dialog = new session.web.Dialog(this, { title: _t("Fields View Get"), width: '95%' }).open();
                $('<pre>').text(session.web.json_node_to_xml(current_view.fields_view.arch, true)).appendTo(dialog.$element);
                break;
            case 'perm_read':
                var ids = current_view.get_selected_ids();
                if (ids.length === 1) {
                    this.dataset.call('perm_read', [ids]).then(function(result) {
                        var dialog = new session.web.Dialog(this, {
                            title: _.str.sprintf(_t("View Log (%s)"), self.dataset.model),
                            width: 400
                        }, QWeb.render('ViewManagerDebugViewLog', {
                            perm : result[0],
                            format : session.web.format_value
                        })).open();
                    });
                }
                break;
            case 'fields':
                this.dataset.call_and_eval(
                        'fields_get', [false, {}], null, 1).then(function (fields) {
                    var $root = $('<dl>');
                    _(fields).each(function (attributes, name) {
                        $root.append($('<dt>').append($('<h4>').text(name)));
                        var $attrs = $('<dl>').appendTo(
                                $('<dd>').appendTo($root));
                        _(attributes).each(function (def, name) {
                            if (def instanceof Object) {
                                def = JSON.stringify(def);
                            }
                            $attrs
                                .append($('<dt>').text(name))
                                .append($('<dd style="white-space: pre-wrap;">').text(def));
                        });
                    });
                    new session.web.Dialog(self, {
                        title: _.str.sprintf(_t("Model %s fields"),
                                             self.dataset.model),
                        width: '95%'}, $root).open();
                });
                break;
            case 'manage_views':
                if (current_view.fields_view && current_view.fields_view.arch) {
                    var view_editor = new session.web.ViewEditor(current_view, current_view.$element, this.dataset, current_view.fields_view.arch);
                    view_editor.start();
                } else {
                    this.do_warn(_t("Manage Views"),
                            _t("Could not find current view declaration"));
                }
                break;
            case 'edit_workflow':
                return this.do_action({
                    res_model : 'workflow',
                    domain : [['osv', '=', this.dataset.model]],
                    views: [[false, 'list'], [false, 'form'], [false, 'diagram']],
                    type : 'ir.actions.act_window',
                    view_type : 'list',
                    view_mode : 'list'
                });
                break;
            case 'edit':
                this.do_edit_resource($option.data('model'), $option.data('id'), { name : $option.text() });
                break;
            default:
                if (val) {
                    console.log("No debug handler for ", val);
                }
        }
        evt.currentTarget.selectedIndex = 0;
    },
    do_edit_resource: function(model, id, action) {
        var action = _.extend({
            res_model : model,
            res_id : id,
            type : 'ir.actions.act_window',
            view_type : 'form',
            view_mode : 'form',
            views : [[false, 'form']],
            target : 'new',
            flags : {
                action_buttons : true,
                form : {
                    resize_textareas : true
                }
            }
        }, action || {});
        this.do_action(action);
    },
    on_mode_switch: function (view_type, no_store) {
        var self = this;

        return $.when(this._super(view_type, no_store)).then(function () {
            self.shortcut_check(self.views[view_type]);

            self.$element.find('.oe-view-manager-logs:first').addClass('oe-folded').removeClass('oe-has-more').css('display','none').find('ul').empty();

            var controller = self.views[self.active_view].controller,
                fvg = controller.fields_view,
                view_id = (fvg && fvg.view_id) || '--';
            self.$element.find('.oe_debug_view').html(QWeb.render('ViewManagerDebug', {
                view: controller,
                view_manager: self
            }));
            if (!self.action.name && fvg) {
                self.$element.find('.oe_view_title_text').text(fvg.arch.attrs.string || fvg.name);
            }

            var $title = self.$element.find('.oe_view_title_text'),
                $search_prefix = $title.find('span.oe_searchable_view');
            if (controller.searchable !== false && self.flags.search_view !== false) {
                if (!$search_prefix.length) {
                    $title.prepend('<span class="oe_searchable_view">' + _t("Search: ") + '</span>');
                }
            } else {
                $search_prefix.remove();
            }
        });
    },
    do_push_state: function(state) {
        if (this.widget_parent && this.widget_parent.do_push_state) {
            state["view_type"] = this.active_view;
            this.widget_parent.do_push_state(state);
        }
    },
    do_load_state: function(state, warm) {
        var self = this,
            defs = [];
        if (state.view_type && state.view_type !== this.active_view) {
            defs.push(
                this.views[this.active_view].deferred.pipe(function() {
                    return self.on_mode_switch(state.view_type, true);
                })
            );
        } 

        $.when(this.views[this.active_view] ? this.views[this.active_view].deferred : $.when(), defs).then(function() {
            self.views[self.active_view].controller.do_load_state(state, warm);
        });
    },
    shortcut_check : function(view) {
        var self = this;
        var grandparent = this.widget_parent && this.widget_parent.widget_parent;
        // display shortcuts if on the first view for the action
        var $shortcut_toggle = this.$element.find('.oe-shortcut-toggle');
        if (!this.action.name ||
            !(view.view_type === this.views_src[0].view_type
                && view.view_id === this.views_src[0].view_id)) {
            $shortcut_toggle.hide();
            return;
        }
        $shortcut_toggle.removeClass('oe-shortcut-remove').show();
        if (_(this.session.shortcuts).detect(function (shortcut) {
                    return shortcut.res_id === self.session.active_id; })) {
            $shortcut_toggle.addClass("oe-shortcut-remove");
        }
        this.shortcut_add_remove();
    },
    shortcut_add_remove: function() {
        var self = this;
        var $shortcut_toggle = this.$element.find('.oe-shortcut-toggle');
        $shortcut_toggle
            .unbind("click")
            .click(function() {
                if ($shortcut_toggle.hasClass("oe-shortcut-remove")) {
                    $(self.session.shortcuts.binding).trigger('remove-current');
                    $shortcut_toggle.removeClass("oe-shortcut-remove");
                } else {
                    $(self.session.shortcuts.binding).trigger('add', {
                        'user_id': self.session.uid,
                        'res_id': self.session.active_id,
                        'resource': 'ir.ui.menu',
                        'name': self.action.name
                    });
                    $shortcut_toggle.addClass("oe-shortcut-remove");
                }
            });
    },
    /**
     * Intercept do_action resolution from children views
     */
    on_action_executed: function () {
        return new session.web.DataSet(this, 'res.log')
                .call('get', [], this.do_display_log);
    },
    /**
     * @param {Array<Object>} log_records
     */
    do_display_log: function (log_records) {
        var self = this;
        var cutoff = 3;
        var $logs = this.$element.find('.oe-view-manager-logs:first').addClass('oe-folded').css('display', 'block');
        var $logs_list = $logs.find('ul').empty();
        $logs.toggleClass('oe-has-more', log_records.length > cutoff);
        _(log_records.reverse()).each(function (record) {
            var context = {};
            if (record.context) {
                try { context = py.eval(record.context).toJSON(); }
                catch (e) { /* TODO: what do I do now? */ }
            }
            $(_.str.sprintf('<li><a href="#">%s</a></li>', record.name))
                .appendTo($logs_list)
                .delegate('a', 'click', function () {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: record.res_model,
                        res_id: record.res_id,
                        // TODO: need to have an evaluated context here somehow
                        context: context,
                        views: [[context.view_id || false, 'form']]
                    });
                    return false;
                });
        });
    },
    display_title: function () {
        return this.action.name;
    }
});

session.web.Sidebar = session.web.OldWidget.extend({
    init: function(parent, element_id) {
        this._super(parent, element_id);
        this.items = {};
        this.sections = {};
    },
    start: function() {
        this._super(this);
        var self = this;
        this.$element.html(session.web.qweb.render('Sidebar'));
        this.$element.find(".toggle-sidebar").click(function(e) {
            self.do_toggle();
        });
    },
    add_default_sections: function() {
        var self = this,
            view = this.widget_parent,
            view_manager = view.widget_parent,
            action = view_manager.action;
        if (this.session.uid === 1) {
            this.add_section(_t('Customize'), 'customize');
            this.add_items('customize', [{
                label: _t("Translate"),
                callback: view.on_sidebar_translate,
                title: _t("Technical translation")
            }]);
        }

        this.add_section(_t('Other Options'), 'other');
        this.add_items('other', [
            {
                label: _t("Import"),
                callback: view.on_sidebar_import
            }, {
                label: _t("Export"),
                callback: view.on_sidebar_export
            }
        ]);
    },

    add_toolbar: function(toolbar) {
        var self = this;
        _.each([['print', _t("Reports")], ['action', _t("Actions")], ['relate', _t("Links")]], function(type) {
            var items = toolbar[type[0]];
            if (items.length) {
                for (var i = 0; i < items.length; i++) {
                    items[i] = {
                        label: items[i]['name'],
                        action: items[i],
                        classname: 'oe_sidebar_' + type[0]
                    }
                }
                self.add_section(type[1], type[0]);
                self.add_items(type[0], items);
            }
        });
    },

    add_section: function(name, code) {
        if(!code) code = _.str.underscored(name);
        var $section = this.sections[code];

        if(!$section) {
            var section_id = _.uniqueId(this.element_id + '_section_' + code + '_');
            $section = $(session.web.qweb.render("Sidebar.section", {
                section_id: section_id,
                name: name,
                classname: 'oe_sidebar_' + code
            }));
            $section.appendTo(this.$element.find('div.sidebar-actions'));
            this.sections[code] = $section;
        }
        return $section;
    },
    /**
     * For each item added to the section:
     *
     * ``label``
     *     will be used as the item's name in the sidebar
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
        var self = this,
            $section = this.add_section(_.str.titleize(section_code.replace('_', ' ')), section_code),
            section_id = $section.attr('id');

        if (items) {
            for (var i = 0; i < items.length; i++) {
                items[i].element_id = _.uniqueId(section_id + '_item_');
                this.items[items[i].element_id] = items[i];
            }

            var $items = $(session.web.qweb.render("Sidebar.section.items", {items: items}));

            $items.find('a.oe_sidebar_action_a').click(function() {
                var item = self.items[$(this).attr('id')];
                if (item.callback) {
                    item.callback.apply(self, [item]);
                }
                if (item.action) {
                    self.on_item_action_clicked(item);
                }
                return false;
            });

            var $ul = $section.find('ul');
            if(!$ul.length) {
                $ul = $('<ul/>').appendTo($section);
            }
            $items.appendTo($ul);
        }
    },
    on_item_action_clicked: function(item) {
        var self = this;
        self.widget_parent.sidebar_context().then(function (context) {
            var ids = self.widget_parent.get_selected_ids();
            if (ids.length == 0) {
                //TODO: make prettier warning?
                $("<div />").text(_t("You must choose at least one record.")).dialog({
                    title: _t("Warning"),
                    modal: true
                });
                return false;
            }
            var additional_context = _.extend({
                active_id: ids[0],
                active_ids: ids,
                active_model: self.widget_parent.dataset.model
            }, context);
            self.rpc("/web/action/load", {
                action_id: item.action.id,
                context: additional_context
            }, function(result) {
                result.result.context = _.extend(result.result.context || {},
                    additional_context);
                result.result.flags = result.result.flags || {};
                result.result.flags.new_window = true;
                self.do_action(result.result, function () {
                    // reload view
                    self.widget_parent.reload();
                });
            });
        });
    },
    do_fold: function() {
        this.$element.addClass('closed-sidebar').removeClass('open-sidebar');
    },
    do_unfold: function() {
        this.$element.addClass('open-sidebar').removeClass('closed-sidebar');
    },
    do_toggle: function() {
        this.$element.toggleClass('open-sidebar closed-sidebar');
    }
});

session.web.TranslateDialog = session.web.Dialog.extend({
    dialog_title: {toString: function () { return _t("Translations"); }},
    init: function(view) {
        // TODO fme: should add the language to fields_view_get because between the fields view get
        // and the moment the user opens the translation dialog, the user language could have been changed
        this.view_language = view.session.user_context.lang;
        this['on_button_' + _t("Save")] = this.on_btn_save;
        this['on_button_' + _t("Close")] = this.on_btn_close;
        this._super(view, {
            width: '80%',
            height: '80%'
        });
        this.view = view;
        this.view_type = view.fields_view.type || '';
        this.$fields_form = null;
        this.$view_form = null;
        this.$sidebar_form = null;
        this.translatable_fields_keys = _.map(this.view.translatable_fields || [], function(i) { return i.name });
        this.languages = null;
        this.languages_loaded = $.Deferred();
        (new session.web.DataSetSearch(this, 'res.lang', this.view.dataset.get_context(),
            [['translatable', '=', '1']])).read_slice(['code', 'name'], { sort: 'id' }).then(this.on_languages_loaded);
    },
    start: function() {
        var self = this;
        this._super();
        $.when(this.languages_loaded).then(function() {
            self.$element.html(session.web.qweb.render('TranslateDialog', { widget: self }));
            self.$fields_form = self.$element.find('.oe_translation_form');
            self.$fields_form.find('.oe_trad_field').change(function() {
                $(this).toggleClass('touched', ($(this).val() != $(this).attr('data-value')));
            });
        });
        return this;
    },
    on_languages_loaded: function(langs) {
        this.languages = langs;
        this.languages_loaded.resolve();
    },
    do_load_fields_values: function(callback) {
        var self = this,
            deffered = [];
        this.$fields_form.find('.oe_trad_field').val('').removeClass('touched');
        _.each(self.languages, function(lg) {
            var deff = $.Deferred();
            deffered.push(deff);
            var callback = function(values) {
                _.each(self.translatable_fields_keys, function(f) {
                    self.$fields_form.find('.oe_trad_field[name="' + lg.code + '-' + f + '"]').val(values[0][f] || '').attr('data-value', values[0][f] || '');
                });
                deff.resolve();
            };
            if (lg.code === self.view_language) {
                var values = {};
                _.each(self.translatable_fields_keys, function(field) {
                    values[field] = self.view.fields[field].get_value();
                });
                callback([values]);
            } else {
                self.rpc('/web/dataset/get', {
                    model: self.view.dataset.model,
                    ids: [self.view.datarecord.id],
                    fields: self.translatable_fields_keys,
                    context: self.view.dataset.get_context({
                        'lang': lg.code
                    })}, callback);
            }
        });
        $.when.apply(null, deffered).then(callback);
    },
    open: function(field) {
        var self = this,
            sup = this._super;
        $.when(this.languages_loaded).then(function() {
            if (self.view.translatable_fields && self.view.translatable_fields.length) {
                self.do_load_fields_values(function() {
                    sup.call(self);
                    if (field) {
                        var $field_input = self.$element.find('tr[data-field="' + field.name + '"] td:nth-child(2) *:first-child');
                        self.$element.scrollTo($field_input);
                        $field_input.focus();
                    }
                });
            } else {
                sup.call(self);
            }
        });
    },
    on_btn_save: function() {
        var trads = {},
            self = this,
            trads_mutex = new $.Mutex();
        self.$fields_form.find('.oe_trad_field.touched').parents('tr').each(function() {
            $(this).find('.oe_trad_field').each(function() {
                var field = $(this).attr('name').split('-');
                if (!trads[field[0]]) {
                    trads[field[0]] = {};
                }
                trads[field[0]][field[1]] = $(this).val();
            });
        });
        _.each(trads, function(data, code) {
            if (code === self.view_language) {
                _.each(data, function(value, field) {
                    self.view.fields[field].set_value(value);
                });
            }
            trads_mutex.exec(function() {
                return self.view.dataset.write(self.view.datarecord.id, data, { context : { 'lang': code } });
            });
        });
        this.close();
    },
    on_btn_close: function() {
        this.close();
    }
});

session.web.View = session.web.Widget.extend(/** @lends session.web.View# */{
    template: "EmptyComponent",
    // name displayed in view switchers
    display_name: '',
    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.dataset = dataset;
        this.view_id = view_id;
        this.set_default_options(options);
    },
    set_default_options: function(options) {
        this.options = options || {};
        _.defaults(this.options, {
            // All possible views options should be defaulted here
            sidebar_id: null,
            sidebar: true,
            action: null,
            action_views_ids: {}
        });
    },
    open_translate_dialog: function(field) {
        if (!this.translate_dialog) {
            this.translate_dialog = new session.web.TranslateDialog(this).start();
        }
        this.translate_dialog.open(field);
    },
    /**
     * Fetches and executes the action identified by ``action_data``.
     *
     * @param {Object} action_data the action descriptor data
     * @param {String} action_data.name the action name, used to uniquely identify the action to find and execute it
     * @param {String} [action_data.special=null] special action handlers (currently: only ``'cancel'``)
     * @param {String} [action_data.type='workflow'] the action type, if present, one of ``'object'``, ``'action'`` or ``'workflow'``
     * @param {Object} [action_data.context=null] additional action context, to add to the current context
     * @param {session.web.DataSet} dataset a dataset object used to communicate with the server
     * @param {Object} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_closed callback to execute when dialog is closed or when the action does not generate any result (no new action)
     */
    do_execute_action: function (action_data, dataset, record_id, on_closed) {
        var self = this;
        var result_handler = function () {
            if (on_closed) { on_closed.apply(null, arguments); }
            if (self.widget_parent && self.widget_parent.on_action_executed) {
                return self.widget_parent.on_action_executed.apply(null, arguments);
            }
        };
        var context = new session.web.CompoundContext(dataset.get_context(), action_data.context || {});

        var handler = function (r) {
            var action = r.result;
            if (action && action.constructor == Object) {
                var ncontext = new session.web.CompoundContext(context);
                if (record_id) {
                    ncontext.add({
                        active_id: record_id,
                        active_ids: [record_id],
                        active_model: dataset.model
                    });
                }
                ncontext.add(action.context || {});
                return self.rpc('/web/session/eval_domain_and_context', {
                    contexts: [ncontext],
                    domains: []
                }).pipe(function (results) {
                    action.context = results.context;
                    /* niv: previously we were overriding once more with action_data.context,
                     * I assumed this was not a correct behavior and removed it
                     */
                    return self.do_action(action, result_handler);
                }, null);
            } else {
                return result_handler();
            }
        };

        if (action_data.special) {
            return handler({result: {"type":"ir.actions.act_window_close"}});
        } else if (action_data.type=="object") {
            var args = [[record_id]], additional_args = [];
            if (action_data.args) {
                try {
                    // Warning: quotes and double quotes problem due to json and xml clash
                    // Maybe we should force escaping in xml or do a better parse of the args array
                    additional_args = JSON.parse(action_data.args.replace(/'/g, '"'));
                    args = args.concat(additional_args);
                } catch(e) {
                    console.error("Could not JSON.parse arguments", action_data.args);
                }
            }
            args.push(context);
            return dataset.call_button(action_data.name, args, handler);
        } else if (action_data.type=="action") {
            return this.rpc('/web/action/load', {
                action_id: parseInt(action_data.name, 10),
                context: context,
                do_not_eval: true
            }).then(handler);
        } else  {
            return dataset.exec_workflow(record_id, action_data.name, handler);
        }
    },
    /**
     * Directly set a view to use instead of calling fields_view_get. This method must
     * be called before start(). When an embedded view is set, underlying implementations
     * of session.web.View must use the provided view instead of any other one.
     *
     * @param embedded_view A view.
     */
    set_embedded_view: function(embedded_view) {
        this.embedded_view = embedded_view;
        this.options.sidebar = false;
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    do_push_state: function(state) {
        if (this.widget_parent && this.widget_parent.do_push_state) {
            this.widget_parent.do_push_state(state);
        }
    },
    do_load_state: function(state, warm) {
    },
    /**
     * Switches to a specific view type
     *
     * @param {String} view view type to switch to
     */
    do_switch_view: function(view) { 
    },
    /**
     * Cancels the switch to the current view, switches to the previous one
     *
     * @param {Object} [options]
     * @param {Boolean} [options.created=false] resource was created
     * @param {String} [options.default=null] view to switch to if no previous view
     */
    do_prev_view: function (options) {
    },
    do_search: function(view) {
    },
    set_common_sidebar_sections: function(sidebar) {
        sidebar.add_default_sections();
    },
    on_sidebar_import: function() {
        var import_view = new session.web.DataImport(this, this.dataset);
        import_view.start();
    },
    on_sidebar_export: function() {
        var export_view = new session.web.DataExport(this, this.dataset);
        export_view.start();
    },
    on_sidebar_translate: function() {
        return this.do_action({
            res_model : 'ir.translation',
            domain : [['type', '!=', 'object'], '|', ['name', '=', this.dataset.model], ['name', 'ilike', this.dataset.model + ',']],
            views: [[false, 'list'], [false, 'form']],
            type : 'ir.actions.act_window',
            view_type : "list",
            view_mode : "list"
        });
    },
    sidebar_context: function () {
        return $.when();
    },
    /**
     * Asks the view to reload itself, if the reloading is asynchronous should
     * return a {$.Deferred} indicating when the reloading is done.
     */
    reload: function () {
        return $.when();
    }
});

session.web.json_node_to_xml = function(node, human_readable, indent) {
    // For debugging purpose, this function will convert a json node back to xml
    // Maybe useful for xml view editor
    indent = indent || 0;
    var sindent = (human_readable ? (new Array(indent + 1).join('\t')) : ''),
        r = sindent + '<' + node.tag,
        cr = human_readable ? '\n' : '';

    if (typeof(node) === 'string') {
        return sindent + node;
    } else if (typeof(node.tag) !== 'string' || !node.children instanceof Array || !node.attrs instanceof Object) {
        throw("Node a json node");
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
            childs.push(session.web.json_node_to_xml(node.children[i], human_readable, indent + 1));
        }
        r += childs.join(cr);
        r += cr + sindent + '</' + node.tag + '>';
        return r;
    } else {
        return r + '/>';
    }
}

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
