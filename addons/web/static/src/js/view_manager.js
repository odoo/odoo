odoo.define('web.ViewManager', function (require) {
"use strict";

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data_manager = require('web.data_manager');
var framework = require('web.framework');
var Model = require('web.DataModel');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ViewManager = Widget.extend(ControlPanelMixin, {
    className: "o_view_manager_content",
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
        this.registry = core.view_registry;
        this.title = this.action.name;
        _.each(views, function (view) {
            var view_type = view[1] || view.view_type;
            var View = self.registry.get(view_type);
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
                options: view.options || {},
                require_fields: View.prototype.require_fields,
                title: self.title,
                type: view_type,
                view_id: view[0] || view.view_id,
            };
            self.view_order.push(view_descr);
            self.views[view_type] = view_descr;
        });
        this.first_view = this.views[options && options.view_type]; // view to open first
        this.default_view = this.get_default_view();
    },
    willStart: function () {
        var views_def;
        var first_view_to_display = this.first_view || this.default_view;
        if (!first_view_to_display.fields_view || (this.flags.search_view && !this.search_fields_view)) {
            views_def = this.load_views(first_view_to_display.require_fields);
        }
        return $.when(this._super(), views_def);
    },
    /**
     * @return {Deferred} initial view and search view (if any) loading promise
     */
    start: function() {
        var self = this;
        _.each(this.views, function (view) {
            view.options = _.extend({
                action: self.action,
            }, self.flags, self.flags[view.type], view.options);
        });
        if (this.flags.search_view) {
            this.search_view_loaded = this.setup_search_view();
        }
        if (this.flags.views_switcher) {
            this.render_switch_buttons();
        }

        // If a non multi-record first_view is given, switch to it but first push the default_view
        // to the view_stack to complete the breadcrumbs
        if (this.first_view && !this.first_view.multi_record && this.default_view.multi_record) {
            this.default_view.controller = this.create_view(this.default_view);
            this.view_stack.push(this.default_view);
        }
        var view_to_load = this.first_view || this.default_view;
        var options = this.flags[view_to_load] && this.flags[view_to_load].options;
        var main_view_loaded = this.switch_mode(view_to_load.type, options);

        return $.when(this._super(), main_view_loaded, this.search_view_loaded);
    },
    /**
     * Loads all missing field_views of views in this.views and the search view.
     *
     * @param {Boolean} [load_fields] whether or not to load the fields as well
     * @return {Deferred}
     */
    load_views: function (load_fields) {
        var self = this;
        var views = [];
        _.each(this.views, function (view) {
            if (!view.fields_view) {
                views.push([view.view_id, view.type]);
            }
        });
        var options = {
            action_id: this.action.id,
            load_fields: load_fields,
            toolbar: this.flags.sidebar,
        };
        if (this.flags.search_view && !this.search_fields_view) {
            options.load_filters = true;
            var searchview_id = this.action.search_view_id && this.action.search_view_id[0];
            views.push([searchview_id || false, 'search']);
        }
        return data_manager.load_views(this.dataset, views, options).then(function (fields_views) {
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
        var old_view = this.active_view;

        if (!view || this.currently_switching) {
            return $.Deferred().reject();
        } else {
            this.currently_switching = true;  // prevent overlapping switches
        }

        // Ensure that the fields_view has been loaded
        var views_def;
        if (!view.fields_view) {
            views_def = this.load_views(view.require_fields);
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
                if (!view.controller) {
                    view.controller = self.create_view(view, view_options);
                }
                view.$fragment = $('<div>');
                view.loaded = view.controller.appendTo(view.$fragment).done(function () {
                    // Remove the unnecessary outer div
                    view.$fragment = view.$fragment.contents();
                    self.trigger("controller_inited", view.type, view.controller);
                });
            }

            self.active_search = $.Deferred();
            // Call do_search on the searchview to compute domains, contexts and groupbys
            if (self.search_view_loaded &&
                    self.flags.auto_search &&
                    view.controller.searchable !== false) {
                $.when(self.search_view_loaded, view.loaded).done(function() {
                    self.searchview.do_search();
                });
            } else {
                self.active_search.resolve();
            }

            return $.when(view.loaded, self.active_search, self.search_view_loaded)
                .then(function() {
                    return self._display_view(view_options, old_view).then(function() {
                        self.trigger('switch_mode', view_type, view_options);
                    });
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
    _display_view: function (view_options, old_view) {
        var self = this;
        var view_controller = this.active_view.controller;
        var view_fragment = this.active_view.$fragment;
        var view_control_elements = this.render_view_control_elements();

        // Show the view
        return $.when(view_controller.do_show(view_options)).done(function () {
            // Prepare the ControlPanel content and update it
            var cp_status = {
                active_view_selector: '.o_cp_switch_' + self.active_view.type,
                breadcrumbs: self.action_manager && self.action_manager.get_breadcrumbs(),
                cp_content: _.extend({}, self.searchview_elements, view_control_elements),
                hidden: self.flags.headless,
                searchview: self.searchview,
                search_view_hidden: view_controller.searchable === false || view_controller.searchview_hidden,
            };
            self.update_control_panel(cp_status);

            // Detach the old view and store it
            if (old_view && old_view !== self.active_view) {
                // Store the scroll position
                if (self.action_manager && self.action_manager.webclient) {
                    old_view.controller.set_scrollTop(self.action_manager.webclient.get_scrollTop());
                }
                // Do not detach ui-autocomplete elements to let jquery-ui garbage-collect them
                var $to_detach = self.$el.contents().not('.ui-autocomplete');
                old_view.$fragment = framework.detach([{widget: old_view.controller}], {$to_detach: $to_detach});
            }

            // If the user switches from a multi-record to a mono-record view,
            // the action manager should be scrolled to the top.
            if (old_view && old_view.controller.multi_record === true && view_controller.multi_record === false) {
                view_controller.set_scrollTop(0);
            }

            // Append the view fragment to self.$el
            framework.append(self.$el, view_fragment, {
                in_DOM: self.is_in_DOM,
                callbacks: [{widget: view_controller}],
            });
        });
    },
    create_view: function(view, view_options) {
        var self = this;
        var js_class = view.fields_view.arch.attrs && view.fields_view.arch.attrs.js_class;
        var View = this.registry.get(js_class || view.type);
        var options = _.clone(view.options);
        if (view.type === "form" && ((this.action.target === 'new' || this.action.target === 'inline') ||
            (view_options && view_options.mode === 'edit'))) {
            options.initial_mode = options.initial_mode || 'edit';
        }

        var controller = new View(this, this.dataset, view.fields_view, options);

        controller.on('switch_mode', this, this.switch_mode.bind(this));
        controller.on('history_back', this, function () {
            if (self.action_manager) self.action_manager.trigger('history_back');
        });
        controller.on("change:title", this, function() {
            if (self.action_manager && !self.flags.headless) {
                var breadcrumbs = self.action_manager.get_breadcrumbs();
                self.update_control_panel({breadcrumbs: breadcrumbs}, {clear: false});
            }
        });

        return controller;
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
            view_controller.render_buttons($buttons ? $buttons.empty() : elements.$buttons);
            view_controller.render_sidebar(elements.$sidebar);
            view_controller.render_pager(elements.$pager);
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
        if (this.searchview) {
            this.searchview.destroy();
        }

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

        this.searchview.on('search_data', this, this.search.bind(this));
        return $.when(this.searchview.appendTo($("<div>"))).done(function() {
            self.searchview_elements = {};
            self.searchview_elements.$searchview = self.searchview.$el;
            self.searchview_elements.$searchview_buttons = self.searchview.$buttons.contents();
        });
    },
    /**
     * Executed on event "search_data" thrown by the SearchView
     */
    search: function(domains, contexts, groupbys) {
        var self = this;
        var controller = this.active_view.controller; // the correct view must be loaded here
        var action_context = this.action.context || {};
        var view_context = controller.get_context();
        pyeval.eval_domains_and_contexts({
            domains: [this.action.domain || []].concat(domains || []),
            contexts: [action_context, view_context].concat(contexts || []),
            group_by_seq: groupbys || []
        }).done(function (results) {
            if (results.error) {
                self.active_search.resolve();
                throw new Error(
                        _.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                                      JSON.stringify(results.error)));
            }
            self.dataset._model = new Model(
                self.dataset.model, results.context, results.domain);
            var groupby = results.group_by.length ?
                          results.group_by :
                          action_context.group_by;
            if (_.isString(groupby)) {
                groupby = [groupby];
            }
            if (!controller.grouped && !_.isEmpty(groupby)){
                self.dataset.set_sort([]);
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
        if (state.view_type && state.view_type !== this.active_view.type) {
            this.switch_mode(state.view_type, true);
        }
        this.active_view.controller.do_load_state(state, warm);
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
