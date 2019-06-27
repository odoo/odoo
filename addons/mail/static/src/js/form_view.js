odoo.define('mail.FormView', function (require) {
"use strict";

var FormView = require('web.FormView');

/**
 * This file is used to add "message_attachment_count" to fieldsInfo so we can fetch its value for the
 * chatter's attachment button without having it explicitly declared in the form view template.
 *
 */

FormView.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        var fieldsInfo = this.fieldsInfo[this.viewType];
        if ('message_ids' in fieldsInfo && !('message_attachment_count' in fieldsInfo)) {
            fieldsInfo.message_attachment_count = {};
        }
    },
});

});
