import { fields, Record } from "@mail/core/common/record";
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

    /** @type {number} */
    id = fields.Attr(undefined, {
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && !this.isTransient) {
                busService.start();
            }
        },
    });
    thread = fields.One("mail.thread", {
        compute() {
            return { id: this.id, model: "discuss.channel" };
        },
        inverse: "channel",
        onDelete: (r) => r?.delete(),
    });

    /**
     * @returns {boolean} true if the channel was opened, false otherwise
     */
    openChannel() {
        return false;
    }
}

DiscussChannel.register();
