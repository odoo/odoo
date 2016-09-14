odoo.define('web.View', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');

var View = Widget.extend({
    events: {
        'click a[type=action]': function (ev) {
            ev.preventDefault();
            var action_data = $(ev.target).attr('name');
            this.do_action(action_data);
        }
    },
    // name displayed in view switchers
    display_name: '',
    // define a view type for each view to allow automatic call to fields_view_get.
    view_type: undefined,
    // used by views that need a searchview.
    searchable: true,
    // used by views that need a searchview but don't want it to be displayed.
    searchview_hidden: false,
    // multi_record is used to distinguish views displaying a single record
    // (e.g. FormView) from those that display several records (e.g. ListView)
    multi_record: true,
    // icon is the font-awesome icon to display in the view switcher
    icon: 'fa-question',
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
    load_view: function() {
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
            view_loaded_def = this.dataset._model.fields_view_get({
                "view_id": this.view_id,
                "view_type": this.view_type,
                "toolbar": !!this.options.sidebar,
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
        var context = new data.CompoundContext(dataset.get_context(), action_data.context || {});

        // response handler
        var handler = function (action) {
            if (action && action.constructor == Object) {
                // filter out context keys that are specific to the current action.
                // Wrong default_* and search_default_* values will no give the expected result
                // Wrong group_by values will simply fail and forbid rendering of the destination view
                var ncontext = new data.CompoundContext(
                    _.object(_.reject(_.pairs(dataset.get_context().eval()), function(pair) {
                      return pair[0].match('^(?:(?:default_|search_default_|show_).+|.+_view_ref|group_by|group_by_no_leaf|active_id|active_ids)$') !== null;
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
                core.bus.trigger('do_reload_needaction');
            });
        } else if (action_data.type=="action") {
            return this.rpc('/web/action/load', {
                action_id: action_data.name,
                context: _.extend(pyeval.eval('context', context), {'active_model': dataset.model, 'active_ids': dataset.ids, 'active_id': record_id}),
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
        this._super();
        core.bus.trigger('view_shown', this);
    },
    is_active: function () {
        return this.ViewManager.active_view.controller === this;
    },
    /**
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
     * This function should render the buttons of the view, set this.$buttons to
     * the produced jQuery element and define some listeners on it.
     * This function should be called after start().
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the View can insert the buttons somewhere else
     */
    render_buttons: function($node) {
    },
    /**
     * This function should instantiate and render the sidebar of the view, set this.sidebar to
     * the instantiated Sidebar Widget and possibly add custom items in it.
     * This function should be called after start().
     * @param {jQuery} [$node] a jQuery node where the sidebar should be inserted
     * $node may be undefined, in which case the View can insert the sidebar somewhere else
     */
    render_sidebar: function($node) {
    },
    /**
     * This function should render the pager of the view, set this.$pager to
     * the produced jQuery element and define some listeners on it.
     * This function should be called after start().
     * @param {jQuery} [$node] a jQuery node where the pager should be inserted
     * $node may be undefined, in which case the View can insert the pager somewhere else
     */
    render_pager: function($node) {
    },
    /**
     * Switches to a specific view type
     */
    do_switch_view: function() {
        this.trigger.apply(this, ['switch_mode'].concat(_.toArray(arguments)));
    },
    do_search: function(domain, context, group_by) {
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
    get_context: function () {
        return {};
    },
    destroy: function () {
        if (this.$buttons) {
            this.$buttons.off();
        }
        return this._super.apply(this, arguments);
    },
});

return View;

});
