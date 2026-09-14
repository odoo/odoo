import { fields, Record } from "@mail/model/export";

export class DiscussCategory extends Record {
    static _name = "discuss.category";

    setup() {
        super.setup(...arguments);
        this.onChange(
            () => [this.busChannel, this.store.env.services.bus_service],
            function subscribeToBusChannel(busChannel, busService) {
                if (busService && busChannel) {
                    busService.addChannel(busChannel);
                    return () => busService.deleteChannel(busChannel);
                }
            }
        );
    }

    /** @type {string} */
    bus_channel_access_token;
    get busChannel() {
        if (!this.id) {
            return undefined;
        }
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
