import { Store } from "@mail/core/common/store_service";
import { Record } from "@mail/model/record";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

export const GUEST_TOKEN_STORAGE_KEY = "im_livechat_guest_token";
/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.livechat_rule = Record.one("im_livechat.channel.rule");
        this.livechat_available = session.livechatData?.isAvailable;
        this.activeLivechats = Record.many("Thread", {
            inverse: "storeAsActiveLivechats",
            onUpdate() {
                if (this.activeLivechats.some(({ isTransient }) => !isTransient)) {
                    this.store.env.services.bus_service.start();
                }
            },
        });
    },
};
patch(Store.prototype, StorePatch);
