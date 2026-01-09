import { fields, Record } from "@mail/model/export";
import { effectWithCleanup } from "@mail/utils/common/misc";

export class DiscussCategory extends Record {
    static _name = "discuss.category";
    static id = "id";

    static new() {
        /** @type {import("models").DiscussCategory} */
        const category = super.new(...arguments);
        effectWithCleanup({
            effect(busChannel, busService) {
                if (busService && busChannel) {
                    busService.addChannel(busChannel);
                    return () => busService.deleteChannel(busChannel);
                }
            },
            dependencies: (category) => [
                category.busChannel,
                category.store.env.services.bus_service,
            ],
            reactiveTargets: [category],
        });
        return category;
    }

    /** @type {string} */
    bus_channel_access_token;
    get busChannel() {
        const channel = `discuss.category_${this.id}`;
        return this.bus_channel_access_token ? `${channel}_${this.bus_channel_access_token}` : channel;
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
