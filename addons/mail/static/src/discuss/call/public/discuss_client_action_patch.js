import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { useState } from "@odoo/owl";
import "@mail/discuss/core/public/discuss_client_action_patch";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useState(useService("discuss.rtc"));
    },
    async joinCallWithWelcomeSettings() {
        if (this.store.discuss_public_thread_data.default_display_mode !== "video_full_screen") {
            return;
        }
        const mute = browser.localStorage.getItem("discuss_call_preview_join_mute") === "true";
        const camera = browser.localStorage.getItem("discuss_call_preview_join_video") === "true";
        await this.rtc.toggleCall(this.store.discuss_public_thread, { audio: !mute, camera });
    },
    async restoreDiscussThread() {
        await super.restoreDiscussThread(...arguments);
        if (!this.store.discuss.thread) {
            return;
        }
        if (this.publicState.welcome) {
            return;
        }
        await this.joinCallWithWelcomeSettings();
    },
    closeWelcomePage() {
        super.closeWelcomePage(...arguments);
        this.joinCallWithWelcomeSettings();
    },
});
