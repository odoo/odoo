odoo.define('web.View', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
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
    defaults: {
        action: {},
    },
    // name displayed in view switchers
    display_name: '',
    // used by views that need a searchview.
    searchable: true,
    // used by views that need a searchview but don't want it to be displayed.
    searchview_hidden: false,
    // multi_record is used to distinguish views displaying a single record
    // (e.g. FormView) from those that display several records (e.g. ListView)
    multi_record: true,
    // indicates whether or not the view is mobile-friendly
    mobile_friendly: false,
    // icon is the font-awesome icon to display in the view switcher
    icon: 'fa-question',
    // whether or not the view requires the model's fields to render itself
    require_fields: false,
    init: function(parent, dataset, fields_view, options) {
        this._super(parent);
        this.ViewManager = parent;
        this.dataset = dataset;
        this.model = dataset.model;
        this.fields_view = fields_view;
        this.options = _.defaults({}, options, this.defaults);
    },
    /**
     * Triggers event 'view_loaded'.
     * Views extending start() must call this.super() once they are ready.
     * @return {Deferred}
     */
    start: function() {
        // add classname that reflect the (absence of) access rights
        this.$el.toggleClass('o_cannot_create', !this.is_action_enabled('create'));
        return this._super().then(this.trigger.bind(this, 'view_loaded'));
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
            if (action && action.constructor === Object) {
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
        } else if (action_data.type === "object") {
            var args = record_id ? [[record_id]] : [dataset.ids];
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
        } else if (action_data.type === "action") {
            return data_manager.load_action(action_data.name, _.extend(pyeval.eval('context', context), {
                active_model: dataset.model,
                active_ids: dataset.ids,
                active_id: record_id
            })).then(handler);
        } else  {
            return dataset.exec_workflow(record_id, action_data.name).then(handler);
        }
    },
    do_show: function () {
        this._super();
        core.bus.trigger('view_shown', this);
    },
    do_push_state: function(state) {
        if (this.getParent() && this.getParent().do_push_state) {
            this.getParent().do_push_state(state);
        }
    },
    do_load_state: function (state, warm) {
    },
    /**
     * This function should render the action buttons of the view.
     * It should be called after start().
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the View can insert the buttons somewhere else
     */
    render_buttons: function($node) {
    },
    /**
     * This function should render the sidebar of the view.
     * It should be called after start().
     * @param {jQuery} [$node] a jQuery node where the sidebar should be inserted
     * $node may be undefined, in which case the View can insert the sidebar somewhere else
     */
    render_sidebar: function($node) {
    },
    /**
     * This function should render the pager of the view.
     * It should be called after start().
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
    set_scrollTop: function(scrollTop) {
        this.scrollTop = scrollTop;
    },
    get_scrollTop: function() {
        return this.scrollTop;
    }
});

return View;

});
