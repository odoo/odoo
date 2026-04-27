/** @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    sendWhatsapp() {
        const send = async (thread) => {
            await new Promise((resolve) => {
                this.env.services.action.doAction(
                    {
                        type: "ir.actions.act_window",
                        name: _t("Send WhatsApp Message"),
                        res_model: "whatsapp.composer",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "new",
                        context: {
                            active_model: thread.model,
                            active_id: thread.id,
                        },
                    },
                    { onClose: resolve }
                );
            });
            this.store.Thread.insert({
                model: this.props.threadModel,
                id: this.props.threadId,
            }).fetchNewMessages();
        };
        if (this.state.thread.id) {
            send(this.state.thread);
        } else {
            this.onThreadCreated = send;
            this.props.saveRecord?.();
        }
    },
});
