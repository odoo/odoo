odoo.define('im_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js', function (require) {
'use strict';

const { registerInstancePatchModel } = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.messaging_notification_handler', 'im_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     * @param {Object} param0
     * @param {integer} param0.channelId
     * @param {integer} param0.partner_id
     */
    _handleNotificationChannelTypingStatus(data) {
        const { channelId, partner_id } = data;
        const channel = this.env.models['mail.thread'].insert({
            id: channelId,
            model: 'mail.channel',
        });
        let partnerId;
        if (partner_id === this.env.messaging.publicPartner.id) {
            // Some shenanigans that this is a typing notification
            // from public partner.
            partnerId = channel.correspondent.id;
        } else {
            partnerId = partner_id;
        }
        this._super(Object.assign(data, {
            partner_id: partnerId,
        }));
    },
});

});
