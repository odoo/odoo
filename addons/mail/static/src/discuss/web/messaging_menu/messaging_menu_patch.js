/* @odoo-module */

import { MessagingMenu } from "@mail/web/messaging_menu/messaging_menu";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(MessagingMenu.prototype, "discuss", {
    setup() {
        this._super();
        this.discussStore = useService("discuss.store");
    },
    getChannel(thread) {
        return this.discussStore.channels[createLocalId("discuss.channel", thread.id)];
    },
    /**
     * @override
     */
    comparethreads(a, b) {
        const aCorrespondent =
            this.discussStore.channels[createLocalId("discuss.channel", a.id)].correspondent;
        const bCorrespondent =
            this.discussStore.channels[createLocalId("discuss.channel", b.id)].correspondent;
        if (aCorrespondent === this.store.odoobot && bCorrespondent !== this.store.odoobot) {
            return 1;
        }
        if (bCorrespondent === this.store.odoobot && aCorrespondent !== this.store.odoobot) {
            return -1;
        }
        return this._super(...arguments);
    },
});
