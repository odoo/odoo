/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

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
        this._super(channelId, Object.assign(data, {
            partner_id: partnerId,
            partner_name: partnerName,
        }));
    },
});
