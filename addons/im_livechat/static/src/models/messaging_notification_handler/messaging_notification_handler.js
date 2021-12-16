odoo.define('im_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js', function (require) {
'use strict';

const { registerInstancePatchModel } = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.messaging_notification_handler', 'im_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _handleNotificationChannelTypingStatus(channelId, data) {
        const { partner_id, partner_name } = data;
        const channel = this.env.models['mail.thread'].findFromIdentifyingData({
            id: channelId,
            model: 'mail.channel',
        });
        if (!channel) {
            return;
        }
        let partnerId;
        let partnerName;
        if (this.env.messaging.publicPartners.some(publicPartner => publicPartner.id === partner_id)) {
            // Some shenanigans that this is a typing notification
            // from public partner.
            partnerId = channel.correspondent.id;
            partnerName = channel.correspondent.name;
        } else {
            partnerId = partner_id;
            partnerName = partner_name;
        }
        Object.assign(data, {
            partner_id: partnerId,
            partner_name: partnerName,
        });
        if ('livechat_username' in data) {
            // flux specific, livechat_username is returned instead of name for livechat channels
            delete data.partner_name; // value still present for API compatibility in stable
            this.env.models['mail.partner'].insert({
                id: partnerId,
                livechat_username: data.livechat_username,
            });
        }
        this._super(channelId, data);
    },
});

});
