import { Chatter } from "@mail/chatter/web_portal/chatter";

import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    onPostCallback() {
        super.onPostCallback();
        const commentsCounterEl = document.querySelector(
            ".o_wslides_lesson_nav a[href='#discuss'] span"
        );
        if (commentsCounterEl) {
            commentsCounterEl.textContent = this.state.thread.comments_count;
        }
    },
});
