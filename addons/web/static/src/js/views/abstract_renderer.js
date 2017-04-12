odoo.define('web.AbstractRenderer', function (require) {
"use strict";

/**
 * The renderer should not handle pagination, data loading, or coordination
 * with the control panel. It is only concerned with rendering.
 *
 */

var Widget = require('web.Widget');

return Widget.extend({
    /**
     * @constructor
     * @param {Widget} parent
     * @param {any} state
     * @param {Object} params
     */
    init: function (parent, state, params) {
        this._super(parent);
        this.state = state;
        this.arch = params.arch;
    },
    /**
     * The rendering can be asynchronous (but it is not encouraged). The start
     * method simply makes sure that we render the view.
     *
     * @returns {Deferred}
     */
    start: function () {
        this.$el.addClass(this.arch.attrs.class);
        return $.when(this._render(), this._super());
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns any relevant state that the renderer might want to keep.
     *
     * The idea is that a renderer can be destroyed, then be replaced by another
     * one instantiated with the state from the model and the localState from
     * the renderer, and the end result should be the same.
     *
     * The kind of state that we expect the renderer to have is mostly DOM state
     * such as the scroll position, the currently active tab page, ...
     *
     * This method is called before each updateState, by the controller.
     *
     * @see setLocalState
     * @returns {any}
     */
    getLocalState: function () {
    },
    /**
     * This is the reverse operation from getLocalState.  With this method, we
     * expect the renderer to restore all DOM state, if it is relevant.
     *
     * This method is called after each updateState, by the controller.
     *
     * @see getLocalState
     * @param {any} localState the result of a call to getLocalState
     */
    setLocalState: function (localState) {
    },
    /**
     * update the state of the view.  It always retrigger a full rerender.
     *
     * @param {any} state
     * @param {Object} params
     * @returns {Deferred}
     */
    updateState: function (state, params) {
        this.state = state;
        return this._render();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     *  Render the view
     *
     * @abstract
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        return $.when();
    },
});

});

