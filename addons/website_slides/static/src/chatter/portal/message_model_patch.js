import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
    async remove() {
        const data = await super.remove(...arguments);
        this.store.env.bus.trigger("reload_rating_popup_composer", data);
        const commentsCounterEl = document.querySelector(
            ".o_wslides_lesson_nav a[href='#discuss'] span"
        );
        if (commentsCounterEl) {
            commentsCounterEl.textContent = this.thread.comments_count;
        }
        return data;
    },

    async edit() {
        const data = await super.edit(...arguments);
        if (data) {
            this.store.env.bus.trigger("reload_rating_popup_composer", data);
        }
        return data;
    },
});
