/** @odoo-module */

import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    /** @override */
    get canReplyTo() {
        return super.canReplyTo && !this.message.originThread?.composer?.threadExpired;
    },
    /**
     * @param {MouseEvent} ev
     */
    async onClick(ev) {
        const id = Number(ev.target.dataset.oeId);
        if (ev.target.closest(".o_whatsapp_channel_redirect")) {
            ev.preventDefault();
            let thread = this.store.Thread.get({ model: "discuss.channel", id });
            if (!thread?.hasSelfAsMember) {
                await this.threadService.orm.call("discuss.channel", "add_members", [[id]], {
                    partner_ids: [this.store.user.id],
                });
                thread = this.store.Thread.insert({
                    id,
                    model: "discuss.channel",
                    type: "whatsapp_message",
                });
            }
            this.threadService.open(thread);
            return;
        }
        super.onClick(ev);
    },
});
