/* @odoo-module */

import { Thread } from "@mail/core/thread_model";
import { assignDefined } from "@mail/utils/misc";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, "discuss/core/common", {
    get imgUrl() {
        if (this.type === "channel" || this.type === "group") {
            return url(
                `/discuss/channel/${this.id}/avatar_128`,
                assignDefined({}, { unique: this.channel?.avatarCacheKey })
            );
        }
        if (this.type === "chat") {
            return `/web/image/res.partner/${this.chatPartnerId}/avatar_128`;
        }
        return this._super();
    },
});
