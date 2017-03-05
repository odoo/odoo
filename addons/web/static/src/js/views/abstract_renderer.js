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

    // // this method is used to get local state unknown by renderer parent, but
    // // necessary to restore the renderer to a full state after an update.  For
    // // example, the currently opened tabs in a form view, or the current scrolling
    // // position
    // getLocalState: function () {
    //     // to be implemented by actual renderer
    // },
    // // this method is used after an update (and may also be used after a new renderer
    // // is instantiated).  For example, opening a new record in a form view is
    // // done by instantiating a new renderer.  But the curently opened page should
    // // be maintained if possible.
    // setLocalState: function (local_state) {
    //     // to be implemented by actual renderer
    // },

        // var local_state = this.getLocalState();
        // .then(this.setLocalState.bind(this, local_state));
    // // todo: add and use getWidget method
    // getWidget: function (node) {
    //     // read field type from node
    //     // or get widget name from attrs
    // },
    // },
