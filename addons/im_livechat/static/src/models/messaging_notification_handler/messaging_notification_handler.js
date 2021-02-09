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
        this._super(channelId, Object.assign(data, {
            partner_id: partnerId,
            partner_name: partnerName,
        }));
    },

    /**
     * @private
     * @param {integer} channelId
     * @param {Object} data
     * @param {string} [data.info]
     * @param {boolean} [data.is_typing]
     * @param {integer} [data.last_message_id]
     * @param {integer} [data.partner_id]
     */
    async _handleNotificationChannel(channelId, data) {
        if (data.info && data.info === 'close_livechat_session') {
            return this._handleNotificationChannelCloseLivechatSession(channelId);
        } else {
            this._super.apply(this, arguments)
        }
    },

    /**
     * @private
     * @param {integer} channelId
     */
    _handleNotificationChannelCloseLivechatSession(channelId) {
        const channel = this.env.models['mail.thread'].findFromIdentifyingData({
            id: channelId,
            model: 'mail.channel',
        });
        if (!channel) {
            return;
        }
        channel.disableComposer();
    },

});

});
