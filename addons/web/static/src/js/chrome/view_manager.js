odoo.define('web.ViewManager', function (require) {
"use strict";

var Context = require('web.Context');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var dom = require('web.dom');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var view_registry = require('web.view_registry');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ViewManager = Widget.extend(ControlPanelMixin, {
    className: "o_view_manager_content",
    custom_events: {
        execute_action: function(event) {
            var data = event.data;
            this.do_execute_action(data.action_data, data.model, data.record_id, data.on_closed)
                .then(data.on_success, data.on_fail);
        },
        search: function(event) {
            var d = event.data;
            _.extend(this.env, this._process_search_data(d.domains, d.contexts, d.groupbys));
            this.active_view.controller.reload(this.env);
        },
        switch_view: function(event) {
            if ('res_id' in event.data) {
                this.env.currentId = event.data.res_id;
            }
            var options = {};
            if (event.data.mode) {
                options.mode = event.data.mode;
            }
            this.switch_mode(event.data.view_type, options);
        },
        env_updated: function(event) {
            _.extend(this.env, event.data);
        },
        push_state: function(event) {
            this.do_push_state(event.data);
        },
    },
    /**
     * Called each time the view manager is attached into the DOM
     */
    on_attach_callback: function() {
        this.is_in_DOM = true;
        if (this.active_view && this.active_view.controller.on_attach_callback) {
            this.active_view.controller.on_attach_callback();
        }
    },
    /**
     * Called each time the view manager is detached from the DOM
     */
    on_detach_callback: function() {
        this.is_in_DOM = false;
        if (this.active_view && this.active_view.controller.on_detach_callback) {
            this.active_view.controller.on_detach_callback();
        }
    },
    /**
     * @param {Object} [dataset]
     * @param {Array} [views] List of [view_id, view_type[, fields_view]]
     * @param {Object} [flags] various boolean describing UI state
     */
    init: function(parent, dataset, views, flags, options) {
        var self = this;
        this._super(parent);

        this.action = options && options.action || {};
        this.action_manager = options && options.action_manager;
        this.flags = flags || {};
        this.dataset = dataset;
        this.view_order = [];
        this.views = {};
        this.view_stack = []; // used for breadcrumbs
        this.active_view = null;
        this.registry = view_registry;
        this.title = this.action.name;
        var actionGroupBy = self.action.context.group_by;
        if (!actionGroupBy) {
            actionGroupBy = [];
        } else if (typeof actionGroupBy === 'string') {
            actionGroupBy = [actionGroupBy];
        }
        _.each(views, function (view) {
            var view_type = view[1] || view.view_type;
            var View = self.registry.get(view_type); //.prototype.config.Controller;
            if (!View) {
                console.error("View type", "'"+view_type+"'", "is not present in the view registry.");
                return;
            }
            var view_label = View.prototype.display_name;
            var view_descr = {
                accesskey: View.prototype.accesskey,
                button_label: _.str.sprintf(_t('%(view_type)s view'), {'view_type': (view_label || view_type)}),
                controller: null,
                fields_view: view[2] || view.fields_view,
                icon: View.prototype.icon,
                label: view_label,
                mobile_friendly: View.prototype.mobile_friendly,
                multi_record: View.prototype.multi_record,
                options: _.extend({
                    action: self.action,
                    limit: self.action.limit,
                    views: self.action.views,
                    groupBy: actionGroupBy,
                }, self.flags, self.flags[view_type], view.options),
                searchable: View.prototype.searchable,
                title: self.title,
                type: view_type,
                view_id: view[0] || view.view_id,
            };
            self.view_order.push(view_descr);
            self.views[view_type] = view_descr;
        });
        this.first_view = this.views[options && options.view_type]; // view to open first
        this.default_view = this.get_default_view();

        // env registers properties shared between views
        this.env = {
            modelName: this.dataset.model,
            ids: this.dataset.ids.length ? this.dataset.ids : undefined,
            currentId: this.dataset.ids.length ? this.dataset.ids[this.dataset.index] : undefined,
            domain: undefined,
            context: this.dataset.context,
            groupBy: undefined,
        };
    },
    willStart: function () {
        var views_def;
        var first_view_to_display = this.first_view || this.default_view;
        if (!first_view_to_display.fields_view || (this.flags.search_view && !this.search_fields_view)) {
            views_def = this.load_views();
        }
        return $.when(this._super(), views_def);
    },
    /**
     * @return {Deferred} initial view and search view (if any) loading promise
     */
    start: function() {
        var self = this;
        var _super = this._super.bind(this, arguments);
        var def;
        if (this.flags.search_view) {
            def = this.setup_search_view().then(function() {
                // udpate domain, context and groupby in the env
                var d = self.searchview.build_search_data();
                _.extend(self.env, self._process_search_data(d.domains, d.contexts, d.groupbys));
            });
        }
        return $.when(def).then(function() {
            var defs = [];
            defs.push(_super());

            if (self.flags.views_switcher) {
                self.render_switch_buttons();
            }

            // If a non multi-record first_view is given, switch to it but first push the default_view
            // to the view_stack to complete the breadcrumbs
            if (self.first_view && !self.first_view.multi_record && self.default_view.multi_record) {
                self.view_stack.push(self.default_view);
            }
            var view_to_load = self.first_view || self.default_view;
            var options = _.extend({}, view_to_load.options);
            defs.push(self.switch_mode(view_to_load.type, options));

            return $.when.apply($, defs);
        }).then(function() {
            if (self.flags.on_load) {
                self.flags.on_load(self);
            }
            core.bus.on('clear_uncommitted_changes', self, function(chain_callbacks) {
                chain_callbacks(function() {
                    return self.active_view.controller.canBeDiscarded();
                });
            });
        });
    },
    /**
     * Loads all missing field_views of views in this.views and the search view.
     *
     * @return {Deferred}
     */
    load_views: function () {
        var self = this;
        var views = [];
        _.each(this.views, function (view) {
            if (!view.fields_view) {
                views.push([view.view_id, view.type]);
            }
        });
        var options = {
            action_id: this.action.id,
            toolbar: this.flags.sidebar,
        };
        if (this.flags.search_view && !this.search_fields_view) {
            options.load_filters = true;
            var searchview_id = this.action.search_view_id && this.action.search_view_id[0];
            views.push([searchview_id || false, 'search']);
        }
        var params = {
            model: this.dataset.model,
            context: this.dataset.get_context(),
            views_descr: views,
        };
        return data_manager.load_views(params, options).then(function (fields_views) {
            _.each(fields_views, function (fields_view, view_type) {
                if (view_type === 'search') {
                    self.search_fields_view = fields_view;
                } else {
                    self.views[view_type].fields_view = fields_view;
                }
            });
        });
    },
    /**
     * Returns the default view with the following fallbacks:
     *  - use the default_view defined in the flags, if any
     *  - use the first view in the view_order
     *
     * @returns {Object} the default view
     */
    get_default_view: function() {
        return this.views[this.flags.default_view || this.view_order[0].type];
    },
    switch_mode: function(view_type, view_options) {
        var self = this;
        var view = this.views[view_type];

        if (!view || this.currently_switching) {
            return $.Deferred().reject();
        } else {
            this.currently_switching = true;  // prevent overlapping switches
        }

        var old_view = this.active_view;

        // Ensure that the fields_view has been loaded
        var views_def;
        if (!view.fields_view) {
            views_def = this.load_views();
        }

        return $.when(views_def).then(function () {
            if (view.multi_record) {
                self.view_stack = [];
            } else if (self.view_stack.length > 0 && !(_.last(self.view_stack).multi_record)) {
                // Replace the last view by the new one if both are mono_record
                self.view_stack.pop();
            }
            self.view_stack.push(view);

            self.active_view = view;

            if (!view.loaded) {
                view_options = _.extend({}, view.options, view_options, self.env);
                if (view_options.groupBy && !view_options.groupBy.length) {
                    var actionContext = view_options ? view_options.action.context : {};
                    var actionGroupBy = actionContext.group_by;
                    if (!actionGroupBy) {
                        actionGroupBy = [];
                    } else if (typeof actionGroupBy === 'string') {
                        actionGroupBy = [actionGroupBy];
                    }
                    view_options.groupBy = actionGroupBy;
                }
                view.loaded = $.Deferred();
                self.create_view(view, view_options).then(function(controller) {
                    view.controller = controller;
                    view.$fragment = $('<div>');
                    controller.appendTo(view.$fragment).done(function() {
                        // Remove the unnecessary outer div
                        view.$fragment = view.$fragment.contents();
                        view.loaded.resolve();
                    });
                });
            } else {
                view.loaded = view.loaded.then(function() {
                    view_options = _.extend({}, view_options, self.env);
                    return view.controller.reload(view_options);
                });
            }

            return $.when(view.loaded)
                .then(function() {
                    self._display_view(old_view);
                    self.trigger('switch_mode', view_type, view_options);
                }).fail(function(e) {
                    if (!(e && e.code === 200 && e.data.exception_type)) {
                        self.do_warn(_t("Error"), view.controller.display_name + _t(" view couldn't be loaded"));
                    }
                    // Restore internal state
                    self.active_view = old_view;
                    self.view_stack.pop();
                });
        }).always(function () {
            self.currently_switching = false;
        });
    },
    _display_view: function (old_view) {
        var view_controller = this.active_view.controller;
        var view_fragment = this.active_view.$fragment;

        // Prepare the ControlPanel content and update it
        var view_control_elements = this.render_view_control_elements();
        var cp_status = {
            active_view_selector: '.o_cp_switch_' + this.active_view.type,
            breadcrumbs: this.action_manager && this.action_manager.get_breadcrumbs(),
            cp_content: _.extend({}, this.searchview_elements, view_control_elements),
            hidden: this.flags.headless,
            searchview: this.searchview,
            search_view_hidden: !this.active_view.searchable,
        };
        this.update_control_panel(cp_status);

        // Detach the old view and store it
        if (old_view && old_view !== this.active_view) {
            // Store the scroll position
            if (this.action_manager && this.action_manager.webclient) {
                old_view.controller.setScrollTop(this.action_manager.webclient.getScrollTop());
            }
            // Do not detach ui-autocomplete elements to let jquery-ui garbage-collect them
            var $to_detach = this.$el.contents().not('.ui-autocomplete');
            old_view.$fragment = dom.detach([{widget: old_view.controller}], {$to_detach: $to_detach});
        }

        // If the user switches from a multi-record to a mono-record view,
        // the action manager should be scrolled to the top.
        if (old_view && old_view.controller.multi_record === true && view_controller.multi_record === false) {
            view_controller.setScrollTop(0);
        }

        // Append the view fragment to this.$el
        dom.append(this.$el, view_fragment, {
            in_DOM: this.is_in_DOM,
            callbacks: [{widget: view_controller}],
        });
    },
    create_view: function(view, view_options) {
        var self = this;
        var arch = view.fields_view.arch;
        var View = this.registry.get(arch.attrs.js_class || view.type);
        var params = _.extend({}, view_options);
        if (view.type === "form" && ((this.action.target === 'new' || this.action.target === 'inline') ||
            (view_options && view_options.mode === 'edit'))) {
            params.mode = params.initial_mode || 'edit';
        }

        view = new View(view.fields_view, params);
        return view.getController(this).then(function(controller) {
            controller.on('history_back', this, function() {
                if (self.action_manager) self.action_manager.trigger('history_back');
            });
            controller.on("change:title", this, function() {
                if (self.action_manager && !self.flags.headless) {
                    var breadcrumbs = self.action_manager.get_breadcrumbs();
                    self.update_control_panel({breadcrumbs: breadcrumbs}, {clear: false});
                }
            });
            return controller;
        });
    },
    select_view: function (index) {
        var view_type = this.view_stack[index].type;
        return this.switch_mode(view_type);
    },
    /**
     * Renders the switch buttons for multi- and mono-record views and adds
     * listeners on them, but does not append them to the DOM
     * Sets switch_buttons.$mono and switch_buttons.$multi to send to the ControlPanel
     */
    render_switch_buttons: function() {
        var self = this;

        // Partition the views according to their multi-/mono-record status
        var views = _.partition(this.view_order, function(view) {
            return view.multi_record === true;
        });
        var multi_record_views = views[0];
        var mono_record_views = views[1];

        // Inner function to render and prepare switch_buttons
        var _render_switch_buttons = function(views) {
            if (views.length > 1) {
                var $switch_buttons = $(QWeb.render('ViewManager.switch-buttons', {views: views}));
                // Create bootstrap tooltips
                _.each(views, function(view) {
                    $switch_buttons.filter('.o_cp_switch_' + view.type).tooltip();
                });
                // Add onclick event listener
                $switch_buttons.filter('button').click(_.debounce(function(event) {
                    var view_type = $(event.target).data('view-type');
                    self.switch_mode(view_type);
                }, 200, true));
                return $switch_buttons;
            }
        };

        // Render switch buttons but do not append them to the DOM as this will
        // be done later, simultaneously to all other ControlPanel elements
        this.switch_buttons = {};
        this.switch_buttons.$multi = _render_switch_buttons(multi_record_views);
        this.switch_buttons.$mono = _render_switch_buttons(mono_record_views);
    },
    /**
     * Renders the control elements (buttons, sidebar, pager) of the current view.
     * Fills this.active_view.control_elements dictionnary with the rendered
     * elements and the adequate view switcher, to send to the ControlPanel.
     * Warning: it should be called before calling do_show on the view as the
     * sidebar is extended to listen on the load_record event triggered as soon
     * as do_show is done (the sidebar should thus be instantiated before).
     */
    render_view_control_elements: function() {
        if (!this.active_view.control_elements) {
            var view_controller = this.active_view.controller;
            var $buttons = this.flags.$buttons;
            var elements = {};
            if (!this.flags.headless) {
                elements = {
                    $buttons: $("<div>"),
                    $sidebar: $("<div>"),
                    $pager: $("<div>"),
                };
            }
            view_controller.renderButtons($buttons ? $buttons.empty() : elements.$buttons);
            view_controller.renderSidebar(elements.$sidebar);
            view_controller.renderPager(elements.$pager);
            // Remove the unnecessary outer div
            elements = _.mapObject(elements, function($node) {
                return $node && $node.contents();
            });
            // Use the adequate view switcher (mono- or multi-record)
            if (this.switch_buttons) {
                if (this.active_view.multi_record) {
                    elements.$switch_buttons = this.switch_buttons.$multi;
                } else {
                    elements.$switch_buttons = this.switch_buttons.$mono;
                }
            }

            // Store the rendered elements in the active_view to allow restoring them later
            this.active_view.control_elements = elements;
        }
        return this.active_view.control_elements;
    },
    /**
     * Sets up the current viewmanager's search view.
     * Sets $searchview and $searchview_buttons in searchview_elements to send to the ControlPanel
     */
    setup_search_view: function() {
        var self = this;
        var search_defaults = {};
        var context = this.action.context || [];
        _.each(context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });

        var options = {
            hidden: this.flags.search_view === false,
            disable_custom_filters: this.flags.search_disable_custom_filters,
            $buttons: $("<div>"),
            action: this.action,
            search_defaults: search_defaults,
        };
        // Instantiate the SearchView, but do not append it nor its buttons to the DOM as this will
        // be done later, simultaneously to all other ControlPanel elements
        this.searchview = new SearchView(this, this.dataset, this.search_fields_view, options);

        return $.when(this.searchview.appendTo($("<div>"))).done(function() {
            self.searchview_elements = {};
            self.searchview_elements.$searchview = self.searchview.$el;
            self.searchview_elements.$searchview_buttons = self.searchview.$buttons.contents();
        });
    },
    _process_search_data: function(domains, contexts, groupbys) {
        // var controller = this.active_view.controller; // the correct view must be loaded here
        var action_context = this.action.context || {};
        var view_context = {}; //controller.get_context();
        var results = pyeval.eval_domains_and_contexts({
            domains: [this.action.domain || []].concat(domains || []),
            contexts: [action_context, view_context].concat(contexts || []),
            group_by_seq: groupbys || [],
            eval_context: this.getSession().user_context,
        });
        if (results.error) {
            throw new Error(_.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                            JSON.stringify(results.error)));
        }
        // this.dataset._model = new Model(this.dataset.model, results.context, results.domain);
        // var groupby = results.group_by.length ? results.group_by : action_context.group_by;
        // if (_.isString(groupby)) {
        //     groupby = [groupby];
        // }
        // if (!controller.grouped && !_.isEmpty(groupby)){
        //     this.dataset.set_sort([]);
        // }
        return {
            context: results.context,
            domain: results.domain,
            groupBy: results.group_by,
        };
    },
    do_push_state: function(state) {
        if (this.action_manager) {
            state.view_type = this.active_view.type;
            this.action_manager.do_push_state(state);
        }
    },
    do_load_state: function(state) {
        var stateChanged = false;
        if ('id' in state && state.id !== '' && state.id !== this.env.currentId) {
            this.env.currentId = state.id;
            stateChanged = true;
        }
        if (state.view_type && state.view_type !== this.active_view.type) {
            stateChanged = true;
        }
        if (stateChanged) {
            this.switch_mode(state.view_type);
        }
    },
    /**
     * Fetches and executes the action identified by ``action_data``.
     *
     * @param {Object} action_data the action descriptor data
     * @param {String} action_data.name the action name, used to uniquely identify the action to find and execute it
     * @param {String} [action_data.special=null] special action handlers (currently: only ``'cancel'``)
     * @param {String} [action_data.type='workflow'] the action type, if present, one of ``'object'``, ``'action'`` or ``'workflow'``
     * @param {Object} [action_data.context=null] additional action context, to add to the current context
     * @param {DataSet} dataset a dataset object used to communicate with the server
     * @param {Object} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_closed callback to execute when dialog is closed or when the action does not generate any result (no new action)
     */
    do_execute_action: function (action_data, model, record_id, on_closed) {
        var self = this;
        var result_handler = on_closed || function () {};
        var context = new Context(this.env.context, action_data.context || {});

        // response handler
        var handler = function (action) {
            if (action && action.constructor === Object) {
                // filter out context keys that are specific to the current action.
                // Wrong default_* and search_default_* values will no give the expected result
                // Wrong group_by values will simply fail and forbid rendering of the destination view
                var ncontext = new Context(
                    _.object(_.reject(_.pairs(self.env.context), function(pair) {
                      return pair[0].match('^(?:(?:default_|search_default_|show_).+|.+_view_ref|group_by|group_by_no_leaf|active_id|active_ids)$') !== null;
                    }))
                );
                ncontext.add(action_data.context || {});
                ncontext.add({active_model: self.env.modelName});
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
        } else if (action_data.type === "object") {
            var args = record_id ? [[record_id]] : [this.env.ids];
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
            var dataset = new data.DataSet(this, model, this.env.context);
            return dataset.call_button(action_data.name, args).then(handler);
        } else if (action_data.type === "action") {
            return data_manager.load_action(action_data.name, _.extend(pyeval.eval('context', context), {
                active_model: this.env.modelName,
                active_ids: this.env.ids,
                active_id: record_id
            })).then(handler);
        }
    },
    destroy: function () {
        if (this.control_elements) {
            if (this.control_elements.$switch_buttons) {
                this.control_elements.$switch_buttons.off();
            }
        }
        return this._super.apply(this, arguments);
    },
});

return ViewManager;

});
