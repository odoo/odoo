/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    delete() {
        super.delete(...arguments);
        if (this.model === "discuss.channel") {
            this._store.env.services.bus_service.deleteChannel(this.busChannel);
        }
    },

    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (this.is_pinned) {
            this.isLocallyPinned = false;
        }
        if (this.isLocallyPinned) {
            this._store.env.services["bus_service"].addChannel(this.busChannel);
        } else {
            this._store.env.services["bus_service"].deleteChannel(this.busChannel);
        }
        if (!this.displayToSelf && !this.isLocallyPinned && this.eq(this._store.discuss.thread)) {
            this._store.discuss.thread = undefined;
        }
    },
});
