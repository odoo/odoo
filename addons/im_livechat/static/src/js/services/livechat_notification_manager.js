odoo.define('im_livechat.Manager.Notification', function (require) {
"use strict";

/**
 * Mail Notification Manager
 *
 * This part of the mail manager is responsible for receiving notifications on
 * the longpoll bus, which are data received from the server.
 */
var MailManager = require('mail.Manager');
var session = require('web.session');


MailManager.include({

    //--------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * On receiving a unsubscribe from channel notification, confirm
     * unsubscription from channel and adapt screen accordingly.
     * avoid notification when the chat is closed by operator
     * @override
     * @private
     * @param {Object} data
     * @param {Object} data.id ID of the unsubscribed channel
     */
    _handlePartnerUnsubscribeNotification: function (data) {
        var channel = this.getChannel(data.id);
        var activePartner = data.operator_pid[0] === session.partner_id;
        if (channel && data.channel_type === 'livechat' && activePartner) {
            this._removeChannel(channel);
            this._mailBus.trigger('unsubscribe_from_channel', data.id);
        } else {
            this._super.apply(this, arguments);
        }
    },
});

return MailManager;

});
