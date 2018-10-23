odoo.define('web.ControlPanelController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');

var ControlPanelController = AbstractController.extend({
    custom_events: {
        button_clicked: '_onButtonClicked',
    },

    /**
     * @override
     */
    init: function (parent, model, renderer) {
        this._super.apply(this, arguments);

        this.model = model;
        this.renderer = renderer;

        this.withControlPanel = false;

        // the updateIndex is used to prevent concurrent updates of the control
        // panel depending on asynchronous code to be executed in the wrong order
        this.updateIndex = 0;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the content and displays the ControlPanel
     *
     * @see  ControlPanelRenderer (update)
     */
    update: function (status, options) {
        this.updateIndex++;
        this.renderer.render(status, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * We don't want the ControlPanel to push its state
     * This is necessary to make some tests pass.
     *
     * @todo: see if this is correct, or adapt tests accordingly
     * @override
     */
    _pushState: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onButtonClicked: function (ev) {
        ev.stopPropagation();
        this.trigger_up('execute_action', {
            action_data: ev.data.attrs,
            env: {
                context: {},
                model: this.modelName,
            },
        });
    },
});

return ControlPanelController;

});
