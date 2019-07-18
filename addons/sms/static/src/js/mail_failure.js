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
                body: _t('An error occurred when sending an SMS'),
                id: 'sms_failure',
            });
        }
        return preview;
    },
});

});
