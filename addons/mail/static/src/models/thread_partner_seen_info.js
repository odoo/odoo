/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "ThreadPartnerSeenInfo",
    fields: {
        lastFetchedMessage: one("Message"),
        lastSeenMessage: one("Message"),
        /**
         * Partner that this seen info is related to.
         */
        partner: one("Partner", { identifying: true }),
        /**
         * Thread (channel) that this seen info is related to.
         */
        thread: one("Thread", { inverse: "partnerSeenInfos", identifying: true }),
    },
});
