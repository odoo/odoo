import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    async remove() {
        const data = await super.remove();
        this.rating_value = false;
        this.store.env.bus.trigger("reload_rating_popup_composer", data);
    },

    async edit() {
        const data = await super.edit(...arguments);
        this.store.env.bus.trigger("reload_rating_popup_composer", data);
    },
};
patch(Message.prototype, messagePatch);
