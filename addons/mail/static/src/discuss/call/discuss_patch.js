/* @odoo-module */

import { Call } from "@mail/discuss/call/call";
import { useRtc } from "@mail/discuss/call/rtc_hook";
import { Discuss } from "@mail/discuss_app/discuss";
import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call });

patch(Discuss.prototype, "discuss/call", {
    setup() {
        this._super(...arguments);
        this.rtc = useRtc();
    },
});
