import { fields, Record } from "@mail/model/export";
import { Deferred } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";

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

    get areAllMembersLoaded() {
        return this.member_count === this.channel_member_ids.length;
    }
    channel_member_ids = fields.Many("discuss.channel.member", {
        inverse: "channel_id",
        onDelete: (r) => r?.delete(),
        sort: (m1, m2) => m1.id - m2.id,
    });
    /** @type {"chat"|"channel"|"group"|"livechat"|"whatsapp"|"ai_chat"|"ai_composer"} */
    channel_type;
    chatWindow = fields.One("ChatWindow", {
        inverse: "channel",
    });
    get chatChannelTypes() {
        return ["chat", "group"];
    }
    /** @type {"not_fetched"|"pending"|"fetched"} */
    fetchMembersState = "not_fetched";
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
    /**
     * To be overridden.
     * The purpose is to exclude technical channel_member_ids like bots and avoid
     * "wrong" seen message indicator
     * @returns {import("models").ChannelMember[]}
     */
    get membersThatCanSeen() {
        return this.channel_member_ids;
    }
    /** @type {Number|undefined} */
    member_count;
    get isChatChannel() {
        return this.chatChannelTypes.includes(this.channel?.channel_type);
    }
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
    get unknownMembersCount() {
        return (this.member_count ?? 0) - (this.channel_member_ids.length ?? 0);
    }

    delete() {
        this.chatWindow?.close();
        super.delete(...arguments);
    }

    async fetchChannelMembers() {
        if (this.fetchMembersState === "pending") {
            return;
        }
        const previousState = this.fetchMembersState;
        this.fetchMembersState = "pending";
        const known_member_ids = this.channel_member_ids.map((channelMember) => channelMember.id);
        let data;
        try {
            data = await rpc("/discuss/channel/members", {
                channel_id: this.id,
                known_member_ids: known_member_ids,
            });
        } catch (e) {
            this.fetchMembersState = previousState;
            throw e;
        }
        this.fetchMembersState = "fetched";
        this.store.insert(data);
    }

    /**
     * @returns {boolean} true if the channel was opened, false otherwise
     */
    openChannel() {
        return false;
    }
}

DiscussChannel.register();
