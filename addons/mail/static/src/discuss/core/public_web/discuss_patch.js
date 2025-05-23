import { Discuss } from "@mail/core/public_web/discuss";
import { Call } from "@mail/discuss/call/common/call";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";
import { useService } from "@web/core/utils/hooks";

import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call, PipBanner });

patch(Discuss.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
});
