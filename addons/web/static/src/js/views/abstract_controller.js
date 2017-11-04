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
    events: {
        'click a[type="action"]': '_onActionClicked',
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
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.model = model;
        this.renderer = renderer;
        this.modelName = params.modelName;
        this.handle = params.handle;
        this.activeActions = params.activeActions;
        this.initialState = params.initialState;
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
    /**
     * @override
     */
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
     * Discards the changes made on the record associated to the given ID, or
     * all changes made by the current controller if no recordID is given. For
     * example, when the user open the 'home' screen, the view manager will call
     * this method on the active view to make sure it is ok to open the home
     * screen (and lose all current state).
     *
     * Note that it returns a deferred, because the view could choose to ask the
     * user if he agrees to discard.
     *
     * @param {string} [recordID]
     *        if not given, we consider all the changes made by the controller
     * @returns {Deferred} resolved if properly discarded, rejected otherwise
     */
    discardChanges: function (recordID) {
        return $.when();
    },
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
     * @private
     * @param {Object} [state] information that will be pushed to the outside
     *   world
     */
    _pushState: function (state) {
        this.trigger_up('push_state', state || {});
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
     * @private
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
     * @private
     * @param {OdooEvent} event
     * @param {number} event.data.id The local model ID for the record to be
     *   opened
     * @param {string} [event.data.mode='readonly']
     */
    _onOpenRecord: function (event) {
        event.stopPropagation();
        var record = this.model.get(event.data.id, {raw: true});
        this.trigger_up('switch_view', {
            view_type: 'form',
            res_id: record.res_id,
            mode: event.data.mode || 'readonly',
            model: this.modelName,
        });
    },
    /**
     * When a user clicks on an <a> link with type="action", we need to actually
     * do the action. This kind of links is used a lot in no-content helpers.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onActionClicked: function (event) {
        event.preventDefault();
        this.do_action(event.target.name);
    },

});

return AbstractController;

});
