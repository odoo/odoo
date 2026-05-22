import { fields, Record } from "@mail/model/export";
import { effectWithCleanup } from "@mail/utils/common/misc";

export class DiscussCategory extends Record {
    static _name = "discuss.category";

    static new() {
        /** @type {import("models").DiscussCategory} */
        const category = super.new(...arguments);
        category._registerDisposeFn(
            effectWithCleanup(() => {
                const busChannel = category.busChannel;
                const busService = category.store.env.services.bus_service;
                if (busService && busChannel) {
                    busService.addChannel(busChannel);
                    return () => busService.deleteChannel(busChannel);
                }
            })
        );
        return category;
    }

    /** @type {string} */
    bus_channel_access_token;
    get busChannel() {
        const channel = `discuss.category_${this.id}`;
        return this.bus_channel_access_token
            ? `${channel}_${this.bus_channel_access_token}`
            : channel;
    }
    channel_ids = fields.Many("discuss.channel");
    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {number} */
    sequence;
}

DiscussCategory.register();
