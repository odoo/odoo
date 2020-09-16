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
        const { partner_id } = data;
        const channel = this.env.models['mail.thread'].findFromIdentifyingData({
            __mfield_id: channelId,
            __mfield_model: 'mail.channel',
        });
        if (!channel) {
            return;
        }
        let partnerId;
        if (partner_id === this.env.messaging.__mfield_publicPartner(this).__mfield_id(this)) {
            // Some shenanigans that this is a typing notification
            // from public partner.
            partnerId = channel.__mfield_correspondent(this).__mfield_id(this);
        } else {
            partnerId = partner_id;
        }
        this._super(channelId, Object.assign(data, {
            partner_id: partnerId,
        }));
    },
});

});
