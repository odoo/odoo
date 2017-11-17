odoo.define('mail.basic_model', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');

/**
 * Include the BasicModel to update the datapoint on the model when a
 * message is posted.
 */
BasicModel.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update the message ids on a datapoint.
     *
     * Note that we directly update the res_ids on the datapoint as the message
     * has already been posted ; this change can't be handled 'normally' with
     * x2m commands because the change won't be saved as a normal field.
     *
     * @param {string} id
     * @param {integer[]} msgIDs
     */
    updateMessageIDs: function (id, msgIDs) {
        var element = this.localData[id];
        element.res_ids = msgIDs;
        element.count = msgIDs.length;
    },
});

});
