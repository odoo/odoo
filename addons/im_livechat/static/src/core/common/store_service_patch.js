import { Store } from "@mail/core/common/store_plugin";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        this.activeVisitorLivechats = fields.Many("discuss.channel", {
            inverse: "storeAsActiveVisitorLivechats",
        });
        /** @type {boolean|undefined} */
        this.can_download_transcript = undefined;
        /** @type {string|null} */
        this.guest_token = null;
        this.has_access_livechat = false;
        this.livechat_available = false;
        this.livechat_rule = fields.One("im_livechat.channel.rule");
    },
};
patch(Store.prototype, storePatch);
