import { fields, Record } from "@mail/model/export";
import { effectWithCleanup } from "@mail/utils/common/misc";

const DISPOSE_EFFECT_SYM = Symbol("DISPOSE_EFFECT");

export class DiscussCategory extends Record {
    static _name = "discuss.category";

    static new() {
        /** @type {import("models").DiscussCategory} */
        const category = super.new(...arguments);
        category[DISPOSE_EFFECT_SYM] = effectWithCleanup(() => {
            const busChannel = category.busChannel;
            const busService = category.store.env.services.bus_service;
            if (busService && busChannel) {
                busService.addChannel(busChannel);
                return () => busService.deleteChannel(busChannel);
            }
        });
        return category;
    }

    delete(...args) {
        this[DISPOSE_EFFECT_SYM]();
        super.delete(...args);
    }

    busChannelSubscribed = false;

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
