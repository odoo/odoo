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
    template: "ViewManager",
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
        this.is_in_DOM = false; // used to know if the view manager is attached in the DOM
        _.each(views, function (view) {
            var view_type = view[1] || view.view_type;
            var View = self.registry.get(view_type);
            if (!View) {
                console.error("View type", "'"+view[1]+"'", "is not present in the view registry.");
                return;
            }
            var view_label = View.prototype.display_name;
            var view_descr = {
                accesskey: View.prototype.accesskey,
                button_label: _.str.sprintf(_t('%(view_type)s view'), {'view_type': (view_label || view_type)}),
                controller: null,
                fields_view: view[2] || view.fields_view,
                embedded_view: view.embedded_view,
                icon: View.prototype.icon,
                label: view_label,
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
            view.$container = self.$(".oe-view-manager-view-" + view.type);
        });

        this.$el.addClass("oe_view_manager_" + ((this.action && this.action.target) || 'current'));

        this.control_elements = {};
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

            // Call do_search on the searchview to compute domains, contexts and groupbys
            if (self.search_view_loaded &&
                    self.flags.auto_search &&
                    view.controller.searchable !== false) {
                self.active_search = $.Deferred();
                $.when(self.search_view_loaded, view.loaded).done(function() {
                    self.searchview.do_search();
                });
            }

            return $.when(view.loaded, self.active_search)
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
        this.active_view.$container.show();
        return $.when(view_controller.do_show(view_options)).done(function () {
            // Prepare the ControlPanel content and update it
            var cp_status = {
                active_view_selector: '.oe-cp-switch-' + self.active_view.type,
                breadcrumbs: self.action_manager && self.action_manager.get_breadcrumbs(),
                cp_content: _.extend({}, self.control_elements, view_control_elements),
                hidden: self.flags.headless,
                searchview: self.searchview,
                search_view_hidden: view_controller.searchable === false || view_controller.searchview_hidden,
            };
            self.update_control_panel(cp_status);

            if (old_view) {
                // Detach the old view but not ui-autocomplete elements to let
                // jquery-ui garbage-collect them
                old_view.$container.contents().not('.ui-autocomplete').detach();

                // Hide old view (at first rendering, there is no view to hide)
                if (self.active_view !== old_view) {
                    if (old_view.controller) old_view.controller.do_hide();
                    if (old_view.$container) old_view.$container.hide();
                }
            }

            // Append the view fragment to its $container
            framework.append(self.active_view.$container, view_fragment, self.is_in_DOM);
        });
    },
    create_view: function(view, view_options) {
        var self = this;
        var View = this.registry.get(view.type);
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
     * Renders the switch buttons and adds listeners on them but does not append them to the DOM
     * Sets $switch_buttons in control_elements to send to the ControlPanel
     * @param {Object} [src] the source requesting the switch_buttons
     * @param {Array} [views] the array of views
     */
    render_switch_buttons: function() {
        if (this.flags.views_switcher && this.view_order.length > 1) {
            var self = this;

            // Render switch buttons but do not append them to the DOM as this will
            // be done later, simultaneously to all other ControlPanel elements
            this.control_elements.$switch_buttons = $(QWeb.render('ViewManager.switch-buttons', {views: self.view_order}));

            // Create bootstrap tooltips
            _.each(this.views, function(view) {
                self.control_elements.$switch_buttons.siblings('.oe-cp-switch-' + view.type).tooltip();
            });

            // Add onclick event listener
            this.control_elements.$switch_buttons.siblings('button').click(_.debounce(function(event) {
                var view_type = $(event.target).data('view-type');
                self.switch_mode(view_type);
            }, 200, true));
        }
    },
    /**
     * Renders the control elements (buttons, sidebar, pager) of the current view
     * This must be done when active_search is resolved (for KanbanViews)
     * Fills this.active_view.control_elements dictionnary with the rendered
     * elements and the adequate view switcher, to send to the ControlPanel
     * Warning: it should be called before calling do_show on the view as the
     * sidebar is extended to listen on the load_record event triggered as soon
     * as do_show is done (the sidebar should thus be instantiated before)
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
            // Store the rendered elements in the active_view to allow restoring them later
            this.active_view.control_elements = elements;
        }
        return this.active_view.control_elements;
    },
    /**
     * Sets up the current viewmanager's search view.
     * Sets $searchview and $searchview_buttons in control_elements to send to the ControlPanel
     *
     * @param {Number|false} view_id the view to use or false for a default one
     * @returns {jQuery.Deferred} search view startup deferred
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
            self.control_elements.$searchview = self.searchview.$el;
            self.control_elements.$searchview_buttons = self.searchview.$buttons.contents();
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
        this.active_view.controller.do_load_state(state, warm);
    },
});

return ViewManager;

});
