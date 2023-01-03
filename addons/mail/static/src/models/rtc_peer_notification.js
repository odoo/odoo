/** @odoo-module **/

import { attr, Model } from "@mail/model";

Model({
    name: "RtcPeerNotification",
    fields: {
        channelId: attr({ readonly: true, required: true }),
        event: attr({ readonly: true, required: true }),
        /**
         * States the id of this RTC peer notification. This id does not
         * correspond to any specific value, it is just a unique identifier
         * given by the creator of this record.
         */
        id: attr({ identifying: true }),
        payload: attr({ readonly: true }),
        senderId: attr({ readonly: true, required: true }),
        targetTokens: attr({ readonly: true, required: true }),
    },
});
