import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import "@mail/discuss/core/public/discuss_client_action_patch";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
    async restoreDiscussThread() {
        await super.restoreDiscussThread(...arguments);
        if (!this.store.discuss.thread) {
            return;
        }
        if (
            this.store.is_welcome_page_displayed ||
            this.store.discuss.thread.default_display_mode !== "video_full_screen"
        ) {
            return;
        }
        await this.joinCallWithDefaultSettings();
    },
    closeWelcomePage() {
        super.closeWelcomePage(...arguments);
        if (this.store.discuss.thread.default_display_mode === "video_full_screen") {
            this.joinCallWithDefaultSettings();
        }
    },
});
