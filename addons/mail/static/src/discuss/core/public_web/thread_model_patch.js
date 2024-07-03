import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    delete() {
        if (this.model === "discuss.channel") {
            this.store.env.services.bus_service.deleteChannel(this.busChannel);
        }
        super.delete(...arguments);
    },

    open() {
        if (
            this.store.discuss.isActive &&
            !this.store.env.services.ui.isSmall &&
            this.model === "discuss.channel"
        ) {
            this.setAsDiscussThread();
            return;
        }
        super.open(...arguments);
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
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (!this.displayToSelf && this.model === "discuss.channel") {
            this.isLocallyPinned = true;
        }
    },
});
