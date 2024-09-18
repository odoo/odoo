import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    get onlineMemberStatuses() {
        return ["away", "bot", "online"];
    },
    onLinkFollowed(fromThread) {
        super.onLinkFollowed(...arguments);
        if (!this.env.isSmall && fromThread?.model === "discuss.channel") {
            fromThread.open(true, { autofocus: false });
        }
    },
    sortMembers(m1, m2) {
        return m1.persona.name?.localeCompare(m2.persona.name) || m1.id - m2.id;
    },
};

patch(Store.prototype, storeServicePatch);
