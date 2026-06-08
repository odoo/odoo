import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const ThreadPatch = {
    open(options) {
        if (this.store.fullscreenChannel?.notEq(this.channel)) {
            this.store.rtc.exitFullscreen();
        }
        return super.open(...arguments);
    },
};
patch(Thread.prototype, ThreadPatch);
