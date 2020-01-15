odoo.define('sms.model.MailFailure', function (require) {
'use strict';

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
        if (this._failureType === 'sms') {
            _.extend(preview, {
                id: 'sms_failure',
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
        if (this._failureType === 'sms') {
            return _t("An error occurred when sending an SMS.");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _getPreviewImage() {
        if (this._failureType === 'sms') {
            return '/sms/static/img/sms_failure.svg';
        }
        return this._super(...arguments);
    },
});

});
