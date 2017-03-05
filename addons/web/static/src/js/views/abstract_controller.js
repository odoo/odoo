odoo.define('web.AbstractController', function (require) {
"use strict";

/**
 * The Controller class is the class coordinating the model and the renderer.
 * It is the C in MVC, and is what was formerly known in Odoo as a View.
 *
 * Its role is to listen to events bubbling up from the model/renderer, and call
 * the appropriate methods if necessary.  It also render control panel buttons,
 * and react to changes in the search view.  Basically, all interactions from
 * the renderer/model with the outside world (meaning server/reading in session/
 * reading localstorage, ...) has to go through the controller.
 */

var Widget = require('web.Widget');


var AbstractController = Widget.extend({
    custom_events: {
        open_record: '_onOpenRecord',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {AbstractModel} model
     * @param {AbstractRenderer} renderer
     * @param {object} params
     * @param {string} params.modelName
     * @param {any} [params.handle] a handle that will be given to the model (some id)
     * @param {any} params.initialState the initialState
     * @param {string} [params.noContentHelp]
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.model = model;
        this.renderer = renderer;
        this.modelName = params.modelName;
        this.handle = params.handle;
        this.activeActions = params.activeActions;
        this.initialState = params.initialState;
        this.noContentHelp = params.noContentHelp;
    },
    /**
     * Simply renders and updates the url.
     *
     * @returns {Deferred}
     */
    start: function () {
        return $.when(
            this._super.apply(this, arguments),
            this.renderer.appendTo(this.$el)
        ).then(this._update.bind(this, this.initialState));
    },
    destroy: function () {
        if (this.$buttons) {
            this.$buttons.off();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns any special keys that may be useful when reloading the view to
     * get the same effect.  This is necessary for saving the current view in
     * the favorites.  For example, a graph view might want to add a key to
     * save the current graph type.
     *
     * @returns {Object}
     */
    getContext: function () {
        return {};
    },
    /**
     * @see setScrollTop
     * @returns {number}
     */
    getScrollTop: function () {
        return this.scrollTop;
    },
    /**
     * Returns a title that may be displayed in the breadcrumb area.  For
     * example, the name of the record.
     *
     * Note: this seems wrong right now, it should not be implemented, we have
     * no guarantee that there is a display_name variable in a controller.
     *
     * @returns {string}
     */
    getTitle: function () {
        return this.display_name;
    },
    /**
     * The use of this method is discouraged.  It is still snakecased, because
     * it currently is used in many templates, but we will move to a simpler
     * mechanism as soon as we can.
     *
     * @deprecated
     * @param {string} action type of action, such as 'create', 'read', ...
     * @returns {boolean}
     */
    is_action_enabled: function (action) {
        return this.activeActions[action];
    },
    /**
     * Short helper method to reload the view
     *
     * @param {Object} [params] This object will simply be given to the update
     * @returns {Deferred}
     */
    reload: function (params) {
        return this.update(params || {});
    },
    /**
     * Most likely called by the view manager, this method is responsible for
     * adding buttons in the control panel (buttons such as save/discard/...)
     *
     * Note that there is no guarantee that this method will be called. The
     * controller is supposed to work even without a view manager, for example
     * in the frontend (odoo frontend = public website)
     *
     * @param {jQuery Node} $node
     */
    renderButtons: function ($node) {
    },
    /**
     * For views that require a pager, this method will be called to allow the
     * controller to instantiate and render a pager. Note that in theory, the
     * controller can actually render whatever he wants in the pager zone.  If
     * your view does not want a pager, just let this method empty.
     *
     * @param {Query Node} $node
     */
    renderPager: function ($node) {
    },
    /**
     * Same as renderPager, but for the 'sidebar' zone (the zone with the menu
     * dropdown in the control panel next to the buttons)
     *
     * @param {Query Node} $node
     */
    renderSidebar: function ($node) {
    },
    /**
     * Not sure about this one, it probably needs to be reworked, maybe merged
     * in get/set local state methods.
     *
     * @see getScrollTop
     * @param {number} scrollTop
     */
    setScrollTop: function (scrollTop) {
        this.scrollTop = scrollTop;
    },
    /**
     * This is the main entry point for the controller.  Changes from the search
     * view arrive in this method, and internal changes can sometimes also call
     * this method.  It is basically the way everything notifies the controller
     * that something has changed.
     *
     * The update method is responsible for fetching necessary data, then
     * updating the renderer and wait for the rendering to complete.
     *
     * @param {Object} params will be given to the model and to the renderer
     * @param {Object} [options]
     * @param {boolean} [options.reload=true] if true, the model will reload data
     *
     * @returns {Deferred}
     */
    update: function (params, options) {
        var self = this;
        var shouldReload = (options && 'reload' in options) ? options.reload : true;
        var def = shouldReload ? this.model.reload(this.handle, params) : $.when();
        return def.then(function (handle) {
            self.handle = handle || self.handle; // update handle if we reloaded
            var state = self.model.get(self.handle);
            var localState = self.renderer.getLocalState();
            return self.renderer.updateState(state, params).then(function () {
                self.renderer.setLocalState(localState);
                self._update(state);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method is the way a view can notifies the outside world that
     * something has changed.  The main use for this is to update the url, for
     * example with a new id.
     *
     * @param {Object} [state] information that will be pushed to the outside
     *   world
     */
    _pushState: function (state) {
        this.trigger_up('push_state', state || {});
    },
    /**
     * Hide or show the nocontent helper.  For this, it also remove the renderer
     * from the dom, and reattach it when necessary.
     *
     * This method is a helper for controllers that want to display a help
     * message when no content is available.  It is suggested to override
     * _update to call this method.
     *
     * @param {boolean} hasNoContent
     */
    _toggleNoContentHelper: function (hasNoContent) {
        if (hasNoContent) {
            this.renderer.$el.detach();
            var $msg = $('<div>')
                .addClass('oe_view_nocontent')
                .html(this.noContentHelp);
            this.$el.html($msg);
        } else {
            if (!document.contains(this.renderer.el)) {
                this.$('div.oe_view_nocontent').remove();
                this.$el.append(this.renderer.$el);
            }
        }
    },
    /**
     * This method is called after each update or when the start method is
     * completed.
     *
     * Its primary use is to be used as a hook to update all parts of the UI,
     * besides the renderer.  For example, it may be used to enable/disable
     * some buttons in the control panel, such as the current graph type for a
     * graph view.
     *
     * @param {Object} state the state given by the model
     * @returns {Deferred}
     */
    _update: function (state) {
        this._pushState();
        return $.when();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When an Odoo event arrives requesting a record to be opened, this method
     * gets the res_id, and request a switch view in the appropriate mode
     *
     * Note: this method seems wrong, it relies on the model being a basic model,
     * to get the res_id.  It should receive the res_id in the event data
     * @todo move this to basic controller? or view manager
     *
     * @param {OdooEvent} event
     * @param {number} event.data.id The local model ID for the record to be
     *   opened
     * @param {string} [event.data.mode='readonly']
     */
    _onOpenRecord: function (event) {
        var record = this.model.get(event.data.id, {raw: true});
        this.trigger_up('switch_view', {
            view_type: 'form',
            res_id: record.res_id,
            mode: event.data.mode || 'readonly',
        });
    },

});

return AbstractController;

});

    // do_show: function () {
    //     this._super.apply(this, arguments);
    //     core.bus.trigger('view_shown', this);
    // },
    // do_push_state: function (state) {
    //     if (this.getParent() && this.getParent().do_push_state) {
    //         this.getParent().do_push_state(state);
    //     }
    // },
    // do_load_state: function (state, warm) {
    // },
    /**
     * Switches to a specific view type
     */
    // do_switch_view: function () {
    //     this.trigger.apply(this, ['switch_mode'].concat(_.toArray(arguments)));
    // },
    // hasNoContent: function (state) {
    //     return !state.count  && this.no_content_help;
    // },
    // displayNoContentHelp: function () {
    //     var $msg = $('<div>')
    //         .addClass('oe_view_nocontent')
    //         .html(this.no_content_help);
    //     this.$el.append($msg);
    //     return;
    // },
    // open_record: function (id, options) {
    //     // TODO: move this to view manager at some point
    //     var state = this.model.get(this.db_id);
    //     var record = this.model.get(id);
    //     var res_ids;
    //     if (state.groupedBy.length) {
    //         res_ids = _.pluck(_.flatten(_.pluck(state.data, 'data')), 'res_id');
    //     } else {
    //         res_ids = _.pluck(state.data, 'res_id');
    //     }
    //     options = _.extend({}, options, {
    //         dataset: {
    //             res_ids: res_ids,
    //             current_id: record.res_id,
    //         },
    //     });
    //     this.trigger_up('switch_view', {
    //         view_type: 'form',
    //         options: options,
    //     });
    // },
    // open_dialog: function (event) {
    //     var data = event.data;
    //     data.flags = _.defaults(data.flags || {}, {
    //         mode: 'edit',
    //         footer_to_buttons: true,
    //         action_buttons: false,
    //         headless: true
    //     });
    //     this.do_action({
    //         type: 'ir.actions.act_window',
    //         res_model: data.model || this.model,
    //         res_id: data.id,
    //         view_id: data.view_id,
    //         view_mode: data.type || 'form',
    //         view_type: data.type || 'form',
    //         views: [[false, data.type || 'form']],
    //         target: 'new',
    //         context: data.context,
    //         flags: data.flags,
    //     }, {
    //         on_load: function (action) {
    //             action.viewManager.$('.o_form_statusbar').remove();
    //             data.on_load && data.on_load(action.viewManager);
    //         },
    //     });
    // },
    // _onDeletedRecords: function () {
    //     this.update_state(this.db_id);
    // },
    // update_state: function (db_id) {
    //     this.db_id = db_id;
    //     var state = this.model.get(db_id);
    //     if (state.type === 'record') {
    //         this.set({ title : state.data.id ? state.data.display_name : _t("New") });
    //     }
    //     if (this.pager && this.config.hasPager) {
    //         this.update_pager();
    //     }
    //     if (this.$buttons) {
    //         this.update_buttons();
    //     }
    //     this.$('.oe_view_nocontent').remove();
    //     if (this.hasNoContent(state)) {
    //         if (this.renderer) {
    //             this.renderer.do_hide();
    //         }
    //         this.displayNoContentHelp();
    //         return;
    //     }
    //     if (this.renderer) {
    //         this.update_renderer();
    //         this.renderer.do_show();
    //     }
    //     var params = state.res_id ? {id: state.res_id} : {};
    //     this.do_push_state(params);
    //     core.bus.trigger('view_shown');
    // },
    // reload: function (event) {
    //     var db_id = event && event.data && event.data.db_id;
    //     if (db_id) {
    //         // reload the relational field given its db_id
    //         this.model.reload(db_id).then(this._confirmSave.bind(this, db_id));
    //     } else {
    //         // no db_id given, so reload the main record
    //         return this.model.reload(this.db_id).then(this.update_state.bind(this));
    //     }
    // },
    // update_renderer: function () {
    //     var state = this.model.get(this.db_id);
    //     return this.renderer.update(state);
    // },
    // renderPager: function ($node, options) {
    //     var data = this.model.get(this.db_id, {raw: true});
    //     this.pager = new Pager(this, data.count, data.offset + 1, this.page_size, options);

    //     this.pager.on('pager_changed', this, function (new_state) {
    //         var self = this;
    //         var data = this.model.get(this.db_id);
    //         this.pager.disable();
    //         var limit_changed = (this.page_size !== new_state.limit);
    //         this.page_size = new_state.limit;
    //         this.model
    //             .setLimit(data.id, new_state.limit)
    //             .setOffset(data.id, new_state.current_min - 1)
    //             .reload(data.id)
    //             .then(function (state) {
    //                 self.update_state(state);
    //                 // Reset the scroll position to the top on page changed only
    //                 if (!limit_changed) {
    //                     self.trigger_up('scrollTo', {offset: 0});
    //                 }
    //             })
    //             .then(this.pager.enable.bind(this.pager));
    //     });
    //     this.pager.appendTo($node = $node || this.options.$pager);
    //     this.update_pager();  // to force proper visibility
    // },
    // update_buttons: function () {
    // },
    // update_pager: function () {
    //     var data = this.model.get(this.db_id);
    //     this.pager.updateState({
    //         current_min: data.offset + 1,
    //         size: data.count,
    //     });
    //     var is_pager_visible = (data.type === 'record') || (!!data.count && (data.groupedBy && !data.groupedBy.length));
    //     this.pager.do_toggle(is_pager_visible);
    // },
    // do_search: function (domain, context, group_by) {
    //     var load = this.db_id ? this._reload_data : this._load_data;
    //     return load.call(this, domain, context, group_by).then(this.update_state.bind(this));
    // },
    // _load_data: function (domain, context, group_by) {
    //     return this.model
    //         .load({
    //             type: 'record',
    //             model: this.modelName,
    //             domain: domain,
    //             groupedBy: group_by,
    //             context: context,
    //         });
    // },
    // _reload_data: function (domain, context, group_by) {
    //     return this.model
    //         .setDomain(this.db_id, domain)
    //         .setContext(this.db_id, context)
    //         .setGroupBy(this.db_id, group_by)
    //         .reload(this.db_id);
    // },
    // sidebar_eval_context: function () {
    //     return $.when({});
    // },
    // /**
    //  * Return whether the user can perform a given action (e.g. 'create', 'edit') in this view.
    //  * An action is disabled by setting the corresponding attribute in the view's main element,
    //  * like: <form string="" create="false" edit="false" delete="false">
    //  */
    // is_action_enabled: function (action) {
    //     var attrs = this.fields_view.arch.attrs;
    //     return (action in attrs) ? JSON.parse(attrs[action]) : true;
    // },
    // config: {
    //     openGroupByDefault: false,
    //     page_size: 40,
    //     hasPager: true,  // TODO: change this into false
    //     js_libs: [], // the list of lazy-loaded js dependencies
    //     css_libs: [], // the list of lazy-loaded css dependencies
    // },
    // defaults: {
    //     action: {},
    // },
    // used by views that need a searchview.
    // searchable: true,
    // used by views that need a searchview but don't want it to be displayed.
    // searchview_hidden: false,

    // events: {
    //     'click a[type=action]': function (ev) {
    //         ev.preventDefault();
    //         var action_data = $(ev.target).attr('name');
    //         this.do_action(action_data);
    //     }
    // },

    // custom_events: _.extend({}, FieldManagerMixin.custom_events, {
    //     open_record: function (event) {
    //         this.open_record(event.data.id);
    //     },
    //     reload: 'reload',
    //     open_dialog: 'open_dialog',
    //     close_dialog: function () {
    //         this.do_action({type: 'ir.actions.act_window_close'});
    //     },
    //     // TODO: add open_action, ...
    // }),

