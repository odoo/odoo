/* @odoo-module */

import { DiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";

import { patch } from "@web/core/utils/patch";

/** @type {DiscussCoreCommon} */
const discussCoreCommon = {
    async _handleNotificationNewMessage(...args) {
        // initChannelsUnreadCounter becomes unreliable
        this.store.fetchChannels();
        return super._handleNotificationNewMessage(...args);
    },
};

patch(DiscussCoreCommon.prototype, discussCoreCommon);
