
odoo.define('mail.form_controller', function (require) {
"use strict";

var FormController = require('web.FormController');

/**
 * Include the FormController to update the datapoint on the model when a
 * message is posted.
 */
FormController.include({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        new_message: '_onNewMessage',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     * @param {string} event.data.id datapointID
     * @param {integer[]} event.data.msgIDs list of message ids
     */
    _onNewMessage: function (event) {
        this.model.updateMessageIDs(event.data.id, event.data.msgIDs);
    },
});

});
