import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { Call } from "@mail/discuss/call/common/call";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";
import { useService } from "@web/core/utils/hooks";

import { patch } from "@web/core/utils/patch";

Object.assign(DiscussContent.components, { Call, PipBanner });

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
});
