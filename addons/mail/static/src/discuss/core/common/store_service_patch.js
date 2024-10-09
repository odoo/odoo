import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    get onlineMemberStatuses() {
        return ["away", "bot", "online"];
    },
    async createGroupChat({ default_display_mode, partners_to, name }) {
        const data = await this.env.services.orm.call("discuss.channel", "create_group", [], {
            default_display_mode,
            partners_to,
            name,
        });
        const { Thread } = this.insert(data);
        const [channel] = Thread;
        channel.open();
        return channel;
    },
    onLinkFollowed(fromThread) {
        super.onLinkFollowed(...arguments);
        if (!this.env.isSmall && fromThread?.model === "discuss.channel") {
            fromThread.open(true, { autofocus: false });
        }
    },
    sortMembers(m1, m2) {
        return m1.persona.name?.localeCompare(m2.persona.name) || m1.id - m2.id;
    },
    /** @param {[number]} partnerIds */
    async startChat(partnerIds) {
        const partners_to = [...new Set([this.self.id, ...partnerIds])];
        if (partners_to.length === 1) {
            const chat = await this.joinChat(partners_to[0], true);
            chat.open();
        } else if (partners_to.length === 2) {
            const correspondentId = partners_to.find(
                (partnerId) => partnerId !== this.store.self.id
            );
            const chat = await this.joinChat(correspondentId, true);
            chat.open();
        } else {
            await this.createGroupChat({ partners_to });
        }
    },
};

patch(Store.prototype, storeServicePatch);
