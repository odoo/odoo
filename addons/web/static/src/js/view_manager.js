odoo.define('web.ViewManager', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');

var _t = core._t;

var ViewManager = Widget.extend({
    template: "ViewManager",
    /**
     * @param {Object} [dataset] null object (... historical reasons)
     * @param {Array} [views] List of [view_id, view_type]
     * @param {Object} [flags] various boolean describing UI state
     * @param {Object} [cp_bus] Bus to allow communication with ControlPanel
     */
    init: function(parent, dataset, views, flags, action, cp_bus) {
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
        this.cp_bus = cp_bus;

        _.each(views, function (view) {
            var view_type = view[1] || view.view_type,
                View = core.view_registry.get(view_type, true),
                view_label = View ? View.prototype.display_name: (void 'nope'),
                view_descr = {
                    controller: null,
                    options: view.options || {},
                    view_id: view[0] || view.view_id,
                    type: view_type,
                    label: view_label,
                    embedded_view: view.embedded_view,
                    title: self.title,
                    button_label: View ? _.str.sprintf(_t('%(view_type)s view'), {'view_type': (view_label || view_type)}) : (void 'nope'),
                };
            self.view_order.push(view_descr);
            self.views[view_type] = view_descr;
        });

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
        var default_view = this.get_default_view(),
            default_options = this.flags[default_view] && this.flags[default_view].options;

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

        if (this.cp_bus) {
            // Tell the ControlPanel to setup its search view
            this.search_view_loaded = $.Deferred();
            this.cp_bus.trigger('setup_search_view', this, this.action, this.dataset, this.flags);
            $.when(this.search_view_loaded).then(function() {
                self.searchview.on('search_data', self, self.search);
            });

            // Tell the ControlPanel to render and append the (switch-)buttons to the DOM
            this.cp_bus.trigger('render_buttons', this.views);
            this.cp_bus.trigger('render_switch_buttons', this.view_order);
        }

        _.each(this.views, function (view) {
            // Expose buttons, sidebar and pager elements to the views so that they can insert stuff in them
            view.options = _.extend(view.options, {
                $buttons : self.$ext_buttons ? self.$ext_buttons.find('.oe-' + view.type + '-buttons') : undefined,
                $sidebar : self.$ext_sidebar,
                $pager : self.$ext_pager,
            }, self.flags, self.flags[view.type], view.options);
        });

        // Switch to the default_view to load it
        this.main_view_loaded = this.switch_mode(default_view, null, default_options);

        return $.when(self.main_view_loaded, this.search_view_loaded);
    },
    /**
     * Sets the external nodes in which the ViewManager and its views should insert elements
     * @param {Object} [nodes] a dictionnary of jQuery nodes
     */
    set_external_nodes: function(nodes) {
        this.$ext_buttons = nodes.$buttons;
        this.$ext_sidebar = nodes.$sidebar;
        this.$ext_pager = nodes.$pager;
    },
    /**
     * Executed by the ControlPanel when the searchview requested by this ViewManager is loaded
     * @param {Widget} [searchview] the SearchView
     * @param {Deferred} [search_view_loaded_def] will be resolved when the SearchView is loaded
     */
    set_search_view: function(searchview, search_view_loaded_def) {
        this.searchview = searchview;
        this.search_view_loaded = search_view_loaded_def;
    },
    /**
     * Executed on event "search_data" thrown by the SearchView
     */
    search: function(domains, contexts, groupbys) {
        var self = this,
            controller = this.active_view.controller, // AAB: Correct view must be loaded here
            action_context = this.action.context || {},
            view_context = controller.get_context();
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
            var groupby = results.group_by.length
                        ? results.group_by
                        : action_context.group_by;
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
    get_default_view: function() {
        return this.flags.default_view || this.view_order[0].type;
    },
    switch_mode: function(view_type, no_store, view_options) {
        var self = this,
            view = this.views[view_type];

        if (!view) {
            return $.Deferred().reject();
        }
        if ((view_type !== 'form') && (view_type !== 'diagram')) {
            this.view_stack = [];
        }

        this.view_stack.push(view);

        // Hide active view (at first rendering, there is no view to hide)
        if (this.active_view && this.active_view !== view) {
            if (this.active_view.controller) this.active_view.controller.do_hide();
            if (this.active_view.$container) this.active_view.$container.hide();
        }
        this.active_view = view;

        if (!view.created) {
            view.created = this.create_view.bind(this)(view, view_options);
        }

        // Call do_search on the searchview to compute domains, contexts and groupbys
        if (this.searchview &&
                this.flags.auto_search &&
                view.controller.searchable !== false) {
            this.active_search = $.Deferred();
            $.when(this.search_view_loaded, view.created).done(function() {
                self.searchview.do_search();
            });
        }
        return $.when(view.created, this.active_search).done(function () {
            self._display_view(view_options);
            self.trigger('switch_mode', view_type, no_store, view_options);
        });
    },
    _display_view: function (view_options) {
        var self = this;
        this.active_view.$container.show();
        $.when(this.active_view.controller.do_show(view_options)).done(function () {
            // Tell the ControlPanel to update its elemnts
            if (self.cp_bus) {
                var search_view_hidden = self.active_view.controller.searchable === false;
                var breadcrumbs = self.action_manager.get_breadcrumbs();
                self.cp_bus.trigger("update", self.active_view, search_view_hidden, breadcrumbs);
            }
        });
    },
    create_view: function(view, view_options) {
        var self = this,
            View = this.registry.get(view.type),
            options = _.clone(view.options),
            view_loaded = $.Deferred();

        if (view.type === "form" && ((this.action && (this.action.target === 'new' || this.action.target === 'inline'))
                || (view_options && view_options.mode === 'edit'))) {
            options.initial_mode = 'edit';
        }
        var controller = new View(this, this.dataset, view.view_id, options),
            $container = view.$container;

        $container.hide();
        view.controller = controller;
        view.$container = $container;

        if (view.embedded_view) {
            controller.set_embedded_view(view.embedded_view);
        }
        controller.on('switch_mode', this, this.switch_mode.bind(this));
        controller.on('history_back', this, function () {
            if (self.action_manager) self.action_manager.trigger('history_back');
        });
        controller.on("change:title", this, function() {
            if (self.cp_bus) {
                var breadcrumbs = self.action_manager.get_breadcrumbs();
                self.cp_bus.trigger("update_breadcrumbs", breadcrumbs);
            }
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
     * @returns {Number|Boolean} the view id of the given type, false if not found
     */
    get_view_id: function(view_type) {
        return this.views[view_type] && this.views[view_type].view_id || false;
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
