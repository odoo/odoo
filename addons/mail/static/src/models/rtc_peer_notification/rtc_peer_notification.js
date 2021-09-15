/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

function factory(dependencies) {

    class RTCPeerNotification extends dependencies['mail.model'] {
    }

    RTCPeerNotification.fields = {
        channelId: attr({
            readonly: true,
            required: true,
        }),
        event: attr({
            readonly: true,
            required: true,
        }),
        payload: attr({
            readonly: true,
        }),
        senderId: attr({
            readonly: true,
            required: true,
        }),
        targetTokens: attr({
            readonly: true,
            required: true,
        }),
    };

    RTCPeerNotification.modelName = 'mail.rtc_peer_notification';

    return RTCPeerNotification;
}

registerNewModel('mail.rtc_peer_notification', factory);
