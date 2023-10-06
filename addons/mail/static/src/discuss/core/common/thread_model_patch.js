/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, {
    get imgUrl() {
        if (this.type === "channel" || this.type === "group") {
            return url(
                `/discuss/channel/${this.id}/avatar_128`,
                assignDefined({}, { unique: this.channel?.avatarCacheKey })
            );
        }
        if (this.type === "chat") {
            return `/web/image/res.partner/${this.chatPartner.id}/avatar_128`;
        }
        return super.imgUrl;
    },
    update(data) {
        super.update(data);
        assignDefined(this, data, ["allow_public_upload"]);
    },
});
