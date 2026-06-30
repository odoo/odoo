import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const ThreadPatch = {
    get isCallDisplayedInChatWindow() {
        return (
            super.isCallDisplayedInChatWindow &&
            (this.store.env.services.ui.isSmall || !this.store.discuss.isActive)
        );
    },
};
patch(Thread.prototype, ThreadPatch);
