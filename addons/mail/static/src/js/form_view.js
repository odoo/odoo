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

        if ('message_ids' in this.fieldsInfo[this.viewType]) {
            this.fieldsInfo[this.viewType].message_attachment_count = {};
        }
    },
});

});
