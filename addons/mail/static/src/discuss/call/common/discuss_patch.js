/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { Call } from "@mail/discuss/call/common/call";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call });

patch(Discuss.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useRtc();
    },
});
