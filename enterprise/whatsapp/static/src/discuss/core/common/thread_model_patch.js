import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        this.whatsapp_partner_id = Record.one("Persona");
        this.whatsappMember = Record.one("ChannelMember", {
            /** @this {import("models").Thread} */
            compute() {
                return (
                    this.channel_type === "whatsapp" &&
                    this.channelMembers.find((member) =>
                        member.persona?.eq(this.whatsapp_partner_id)
                    )
                );
            },
        });
    },
    _computeOfflineMembers() {
        const res = super._computeOfflineMembers();
        if (this.channel_type === "whatsapp") {
            return res.filter((member) => member.persona?.notEq(this.whatsapp_partner_id));
        }
        return res;
    },
    get hasMemberList() {
        return this.channel_type === "whatsapp" || super.hasMemberList;
    },
};

patch(Thread.prototype, threadPatch);
