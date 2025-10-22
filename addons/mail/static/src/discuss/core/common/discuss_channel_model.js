import { fields, Record } from "@mail/model/export";
import { Deferred } from "@web/core/utils/concurrency";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static _inherits = { "mail.thread": "thread" };
    static id = "id";

    /**
     * Retrieve an existing channel from the store or fetch it if missing.
     *
     * @param {number} channel_id
     * @return {Promise<DiscussChannel>}
     */
    static getOrFetch(channel_id) {
        const channel = this.store["discuss.channel"].get(channel_id);
        if (channel?.fetchChannelInfoState === "fetched" || channel_id < 0) {
            return Promise.resolve(channel);
        }
        const fetchChannelInfoDeferred = this.store.channelIdsFetchingDeferred.get(channel_id);
        if (fetchChannelInfoDeferred) {
            return fetchChannelInfoDeferred;
        }
        const def = new Deferred();
        this.store.channelIdsFetchingDeferred.set(channel_id, def);
        this.store.fetchChannel(channel_id).then(
            () => {
                this.store.channelIdsFetchingDeferred.delete(channel_id);
                const channel = this.store["discuss.channel"].get(channel_id);
                if (channel?.exists()) {
                    channel.fetchChannelInfoState = "fetched";
                    def.resolve(channel);
                } else {
                    def.resolve();
                }
            },
            () => {
                this.store.channelIdsFetchingDeferred.delete(channel_id);
                const channel = this.store["discuss.channel"].get(channel_id);
                if (channel?.exists()) {
                    def.reject(channel);
                } else {
                    def.reject();
                }
            }
        );
        return def;
    }

    chatWindow = fields.One("ChatWindow", {
        inverse: "channel",
    });
    hasOtherMembersTyping = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return this.otherTypingMembers.length > 0;
        },
    });
    /** @type {number} */
    id = fields.Attr(undefined, {
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && !this.isTransient) {
                busService.start();
            }
        },
    });
    otherTypingMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.typingMembers.filter((member) => !member.persona?.eq(this.store.self));
        },
    });
    thread = fields.One("mail.thread", {
        compute() {
            return { id: this.id, model: "discuss.channel" };
        },
        inverse: "channel",
        onDelete: (r) => r?.delete(),
    });

    typingMembers = fields.Many("discuss.channel.member", { inverse: "channelAsTyping" });

    delete(options = { closeChatWindow: true }) {
        if (this.chatWindow?.exists() && options.closeChatWindow) {
            this.chatWindow.close();
        }
        super.delete(...arguments);
    }

    /**
     * @returns {boolean} true if the channel was opened, false otherwise
     */
    openChannel() {
        return false;
    }
}

DiscussChannel.register();
