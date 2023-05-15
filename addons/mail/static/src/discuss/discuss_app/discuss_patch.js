/* @odoo-module */

import { Discuss } from "@mail/discuss_app/discuss";
import { Call } from "@mail/discuss/rtc/call";
import { createLocalId } from "@mail/utils/misc";
import { useRtc } from "@mail/discuss/rtc/rtc_hook";
import { patch } from "@web/core/utils/patch";

patch(Discuss, "discuss/discuss_app", {
    components: {
        ...Discuss.components,
        Call,
    },
});

patch(Discuss.prototype, "discuss/discuss_app", {
    setup(env, services) {
        this._super(...arguments);
        this.rtc = useRtc();
    },
    getChannel() {
        return this.discussStore.channels[createLocalId("discuss.channel", this.thread.id)];
    },
});
