/* @odoo-module */

import { Thread } from "@mail/core/thread_model";
import { createLocalId } from "@mail/utils/misc";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "discuss", {
    setup() {
        this._super();
        /** @type {import("@mail/discuss/discuss_store_service").Discusstore} */
        this.discussStore = this._store.env.services["discuss.store"];
    },
    /**
     * @override
     */
    get displayName() {
        const channel = this.discussStore.channels[createLocalId("discuss.channel", this.id)];
        if (channel?.type === "chat" && this.chatPartnerId) {
            return (
                this.customName ||
                this._store.personas[createLocalId("partner", this.chatPartnerId)].nameOrDisplayName
            );
        }
        if (channel?.type === "group" && !this.name) {
            const listFormatter = new Intl.ListFormat(
                this._store.env.services["user"].lang.replace("_", "-"),
                { type: "conjunction", style: "long" }
            );
            return listFormatter.format(
                channel.channelMembers.map((channelMember) => channelMember.persona.name)
            );
        }
        return this._super(...arguments);
    },
});
