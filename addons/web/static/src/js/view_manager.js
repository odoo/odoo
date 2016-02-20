odoo.define('web.ViewManager', function (require) {
"use strict";

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var data = require('web.data');
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
     * @param {Object} [dataset] null object (... historical reasons)
     * @param {Array} [views] List of [view_id, view_type]
     * @param {Object} [flags] various boolean describing UI state
     */
    init: function(parent, dataset, views, flags, action, options) {
        if (action) {
            flags = action.flags || {};
            if (!('auto_search' in flags)) {
                flags.auto_search = action.auto_search !== false;
            }
            this.action = action;
            this.action_manager = parent;
            dataset = new data.DataSetSearch(this, action.res_model, action.context, action.domain);
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
        this.views = {};
        this.view_stack = []; // used for breadcrumbs
        this.active_view = null;
        this.registry = core.view_registry;
        this.title = this.action && this.action.name;
        this.is_in_DOM = false; // used to know if the view manager is attached in the DOM
        _.each(views, function (view) {
            var view_type = view[1] || view.view_type;
            var View = core.view_registry.get(view_type, true);
            if (!View) {
                console.error("View type", "'"+view[1]+"'", "is not present in the view registry.");
                return;
            }
            var view_label = View.prototype.display_name;
            var view_descr = {
                    controller: null,
                    options: view.options || {},
                    view_id: view[0] || view.view_id,
                    type: view_type,
                    label: view_label,
                    embedded_view: view.embedded_view,
                    title: self.title,
                    button_label: _.str.sprintf(_t('%(view_type)s view'), {'view_type': (view_label || view_type)}),
                    multi_record: View.prototype.multi_record,
                    accesskey: View.prototype.accesskey,
                    icon: View.prototype.icon,
                };
            self.view_order.push(view_descr);
            self.views[view_type] = view_descr;
        });

        if (options && options.state && options.state.view_type) {
            var view_type = options.state.view_type;
            var view_descr = this.views[view_type];
            this.default_view = view_descr && view_descr.multi_record ? view_type : undefined;
        }

        // Listen to event 'switch_view' indicating that the VM must now display view wiew_type
        this.on('switch_view', this, function(view_type) {
            if (view_type === 'form' && this.active_view && this.active_view.type === 'form') {
                this._display_view(view_type);
            } else {
                this.switch_mode(view_type);
            }
        });
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        var self = this;
        var default_view = this.get_default_view();
        var default_options = this.flags[default_view] && this.flags[default_view].options;

        this._super();

        var views_ids = {};
        _.each(this.views, function (view) {
            views_ids[view.type] = view.view_id;
            view.options = _.extend({
                action : self.action,
                action_views_ids : views_ids,
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

        // Switch to the default_view to load it
        var main_view_loaded = this.switch_mode(default_view, null, default_options);

        return $.when(main_view_loaded, this.search_view_loaded);
    },
    get_default_view: function() {
        return this.default_view || this.flags.default_view || this.view_order[0].type;
    },
    switch_mode: function(view_type, no_store, view_options) {
        var self = this;
        var view = this.views[view_type];
        var old_view = this.active_view;

        if (!view || this.currently_switching) {
            return $.Deferred().reject();
        } else {
            this.currently_switching = true;  // prevent overlapping switches
        }

        if (view.multi_record) {
            this.view_stack = [];
        } else if (this.view_stack.length > 0 && !(_.last(this.view_stack).multi_record)) {
            // Replace the last view by the new one if both are mono_record
            this.view_stack.pop();
        }
        this.view_stack.push(view);
        this.active_view = view;

        if (!view.created) {
            view.created = this.create_view.bind(this)(view, view_options);
        }

        // Call do_search on the searchview to compute domains, contexts and groupbys
        if (this.search_view_loaded &&
                this.flags.auto_search &&
                view.controller.searchable !== false) {
            this.active_search = $.Deferred();
            $.when(this.search_view_loaded, view.created).done(function() {
                self.searchview.do_search();
            });
        }
        var switched = $.when(view.created, this.active_search).then(function () {
            return self._display_view(view_options, old_view).then(function () {
                self.trigger('switch_mode', view_type, no_store, view_options);
            });
        });
        switched.fail(function(e) {
            if (!(e && e.code === 200 && e.data.exception_type)) {
                self.do_warn(_t("Error"), view.controller.display_name + _t(" view couldn't be loaded"));
            }
            // Restore internal state
            self.active_view = old_view;
            self.view_stack.pop();
        });
        switched.always(function () {
            self.currently_switching = false;
        });
        return switched;
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
        var view_loaded = $.Deferred();

        if (view.type === "form" && ((this.action && (this.action.target === 'new' || this.action.target === 'inline')) ||
            (view_options && view_options.mode === 'edit'))) {
            options.initial_mode = options.initial_mode || 'edit';
        }
        var controller = new View(this, this.dataset, view.view_id, options);
        view.controller = controller;
        view.$fragment = $('<div>');

        if (view.embedded_view) {
            controller.set_embedded_view(view.embedded_view);
        }
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
        controller.on('view_loaded', this, function () {
            view_loaded.resolve();
        });

        // render the view in a fragment so that it is appended in the view's
        // $container only when it's ready
        return $.when(controller.appendTo(view.$fragment), view_loaded).done(function () {
            // Remove the unnecessary outer div
            view.$fragment = view.$fragment.contents();
            self.trigger("controller_inited", view.type, controller);
        });
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
            var elements = {};
            if (!this.flags.headless) {
                elements = {
                    $buttons: !this.flags.footer_to_buttons ? $("<div>") : undefined,
                    $sidebar: $("<div>"),
                    $pager: $("<div>"),
                };
            }
            view_controller.render_buttons(elements.$buttons);
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
     * @returns {Number|Boolean} the view id of the given type, false if not found
     */
    get_view_id: function(view_type) {
        return this.views[view_type] && this.views[view_type].view_id || false;
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
            $buttons: $("<div>"),
            action: this.action,
        };
        // Instantiate the SearchView, but do not append it nor its buttons to the DOM as this will
        // be done later, simultaneously to all other ControlPanel elements
        this.searchview = new SearchView(this, this.dataset, view_id, search_defaults, options);

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
        if (state.view_type && state.view_type !== this.active_view.type) {
            // warning: this code relies on the fact that switch_mode has an immediate side
            // effect (setting the 'active_view' to its new value) AND an async effect (the
            // view is created/loaded).  So, the next statement (do_load_state) is executed 
            // on the new view, after it was initialized, but before it is fully loaded and 
            // in particular, before the do_show method is called.
            this.switch_mode(state.view_type, true);
        }
        this.active_view.controller.do_load_state(state, warm);
    },
});

return ViewManager;

});
