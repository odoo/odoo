/* @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined, assignIn } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { toRaw } from "@odoo/owl";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(data);
        if (thread.type === "whatsapp") {
            assignIn(thread, data, ["anonymous_name"]);
        }
        return thread;
    },
});

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if (this.type === "whatsapp") {
            assignDefined(this, data, ["whatsapp_channel_valid_until"]);
            if (!this._store.discuss.whatsapp.threads.includes(this)) {
                this._store.discuss.whatsapp.threads.push(this);
            }
        }
    },

    get imgUrl() {
        if (this.type !== "whatsapp") {
            return super.imgUrl;
        }

        if (this.correspondent) {
            return url(
                `/web/image/res.partner/${this.correspondent.id}/avatar_128`,
                assignDefined({}, { unique: this.correspondent.write_date })
            );
        }
        
        return DEFAULT_AVATAR;
    },

    get isChatChannel() {
        return this.type === "whatsapp" || super.isChatChannel;
    },

    get whatsappChannelValidUntilDatetime() {
        if (!this.whatsapp_channel_valid_until) {
            return undefined;
        }
        return toRaw(deserializeDateTime(this.whatsapp_channel_valid_until));
    },
});
