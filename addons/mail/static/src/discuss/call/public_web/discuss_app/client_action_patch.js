import { DiscussClientAction } from "@mail/core/public_web/discuss_app/client_action";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
    /**
     * Checks if we are in a client action and if we have a query parameter requesting to join a call,
     * if so, the call is joined on the current discuss thread.
     */
    async restoreDiscussThread() {
        const hasFullScreenUrl = new URL(browser.location.href).searchParams.has("fullscreen");
        await super.restoreDiscussThread(...arguments);
        const action = this.props.action;
        if (!action) {
            return;
        }
        const call = action.context?.call || action.params?.call;
        if (call === "accept") {
            await this.rtc.joinCall(this.store.discuss.thread.channel);
            return;
        }
        if (
            hasFullScreenUrl &&
            this.store.discuss.thread?.channel.default_display_mode === "video_full_screen" &&
            this.store.discuss.thread.rtc_session_ids.length > 0
        ) {
            this.joinCallWithDefaultSettings();
        }
    },
    async joinCallWithDefaultSettings() {
        const mute = browser.localStorage.getItem("discuss_call_preview_join_mute") === "true";
        const camera = browser.localStorage.getItem("discuss_call_preview_join_video") === "true";
<<<<<<< 5d18a9e458b9414b32bc9801c6b83bedafc8ad27:addons/mail/static/src/discuss/call/public_web/discuss_app/client_action_patch.js
        await this.rtc.toggleCall(this.store.discuss.thread.channel, { audio: !mute, camera });
||||||| 006220901d6b466fc296edbbcec962d2168a0782:addons/mail/static/src/discuss/call/public_web/discuss_client_action_patch.js
        await this.rtc.toggleCall(this.store.discuss.thread, { audio: !mute, camera });
=======
        const channel = this.store.discuss.thread;
        if (channel.notEq(this.rtc.channel)) {
            await this.rtc.toggleCall(channel, { audio: !mute, camera });
        }
>>>>>>> 21f38098542c3cb6dcd89a77941089691d824e54:addons/mail/static/src/discuss/call/public_web/discuss_client_action_patch.js
        await this.rtc.enterFullscreen();
    },
});
