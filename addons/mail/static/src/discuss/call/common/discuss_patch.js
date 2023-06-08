/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { Call } from "@mail/discuss/call/common/call";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call });

patch(Discuss.prototype, "discuss/call/common", {
    setup() {
        this._super(...arguments);
        this.rtc = useRtc();
    },
});
