import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    delete() {
        if (this.model === "discuss.channel") {
            this.store.env.services.bus_service.deleteChannel(this.busChannel);
        }
        super.delete(...arguments);
    },

    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (this.is_pinned) {
            this.isLocallyPinned = false;
        }
        if (this.isLocallyPinned) {
            this.store.env.services["bus_service"].addChannel(this.busChannel);
        } else {
            this.store.env.services["bus_service"].deleteChannel(this.busChannel);
        }
        if (!this.displayToSelf && !this.isLocallyPinned && this.eq(this.store.discuss.thread)) {
            this.store.discuss.thread = undefined;
        }
    },
});
