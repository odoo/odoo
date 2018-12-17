odoo.define('snailmail.model.MailFailure', function (require) {
"use strict";

var MailFailure = require('mail.model.MailFailure');
var core = require('web.core');
var _t = core._t;

MailFailure.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getPreview: function () {
        var preview = this._super.apply(this, arguments);
        if (this._failureType === 'snailmail') {
            _.extend(preview, {
                body: _t("An error occured when sending a letter with Snailmail"),
                id: 'snailmail_failure',
            });
        }
        return preview;
    },
});

});
