odoo.define('im_livechat.NotificationManager', function (require) {
"use strict";

const MailManager = require('mail.Manager');

MailManager.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called when receiving a notification on a channel (all members of a
     * channel receive this notification)
     *
     * @override
     * @private
     * @param {Object} params
     * @param {Object} params.data
     * @param {boolean} [params.data.no_operator] if set, specify the
     *   visiblity of input box for the threadwindow
     */
    _handleChannelNotification(params) {
        if (params.data && params.data._type === 'operator_status') {
            const threadWindow = this._getThreadWindow(params.channelID);
            if (threadWindow) {
                threadWindow.$input.prop('disabled', params.data.no_operator);
            }
        } else {
            this._super.apply(this, arguments);
        }
    },
});

});
