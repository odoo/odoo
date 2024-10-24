import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { rpc } from "@web/core/network/rpc";
import { Mutex } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
patch(Thread.prototype, {
    setup() {
        super.setup();
        this.operator = Record.one("Persona");
        this.fetchChannelMutex = new Mutex();
        this.fetchChannelInfoDeferred = undefined;
        this.fetchChannelInfoState = "not_fetched";
    },

    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChatChannel() {
        return this.channel_type === "livechat" || super.isChatChannel;
    },
    async fetchLivechatChannelInfo() {
        return this.fetchChannelMutex.exec(async () => {
            if (!(this.localId in this.store.Thread.records)) {
                return; // channel was deleted in-between two calls
            }
            const data = await rpc("/livechat/channel/info", { channel_id: this.id });
            if (data) {
                this.store.insert(data);
            } else {
                this.delete();
            }
            return data ? this : undefined;
        });
    },
});
