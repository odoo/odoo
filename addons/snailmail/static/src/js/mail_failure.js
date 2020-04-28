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
        if (this._messageType === 'snailmail') {
            _.extend(preview, {
                id: 'snailmail_failure',
            });
        }
        return preview;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getPreviewBody() {
        if (this._messageType === 'snailmail') {
            return _t("An error occured when sending a letter with Snailmail.");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _getPreviewImage() {
        if (this._messageType === 'snailmail') {
            return '/snailmail/static/img/snailmail_failure.png';
        }
        return this._super(...arguments);
    },
});

});
