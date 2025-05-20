import { Discuss } from "@mail/core/public_web/discuss";
import { Call } from "@mail/discuss/call/common/call";

import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call });

patch(Discuss.prototype, {
    get rtc() {
        return this.store.rtc;
    },
});
