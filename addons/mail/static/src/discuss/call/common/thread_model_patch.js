import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const ThreadPatch = patchModel(Thread, {
    open(options) {
        if (this.store.fullscreenChannel?.notEq(this.channel)) {
            this.store.rtc.exitFullscreen();
        }
        return super.open(...arguments);
    },
});
