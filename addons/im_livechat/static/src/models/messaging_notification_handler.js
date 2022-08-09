/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging_notification_handler';

patchRecordMethods('MessagingNotificationHandler', {
    /**
     * @override
     */
    _handleNotificationChannelMemberTypingStatus({ channel_id, is_typing, livechat_username, partner_id, partner_name }) {
        const channel = this.messaging.models['Channel'].findFromIdentifyingData({ id: channel_id });
        if (!channel) {
            return;
        }
        let partnerId;
        let partnerName;
        if (this.messaging.publicPartners.some(publicPartner => publicPartner.id === partner_id)) {
            // Some shenanigans that this is a typing notification
            // from public partner.
            partnerId = channel.correspondent.id;
            partnerName = channel.correspondent.name;
        } else {
            partnerId = partner_id;
            partnerName = partner_name;
        }
        const data = {
            channel_id,
            is_typing,
            partner_id: partnerId,
            partner_name: partnerName,
        };
        if (livechat_username) {
            // flux specific, livechat_username is returned instead of name for livechat channels
            delete data.partner_name; // value still present for API compatibility in stable
            this.models['Partner'].insert({
                id: partnerId,
                livechat_username: livechat_username,
            });
        }
        this._super(data);
    },
});
