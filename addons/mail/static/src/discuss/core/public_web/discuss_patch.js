import { Discuss } from "@mail/core/public_web/discuss";
import { Call } from "@mail/discuss/call/common/call";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";
import { useService } from "@web/core/utils/hooks";
import { CALL_FULLSCREEN } from "@mail/discuss/call/common/const";

import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { Call, PipBanner });

patch(Discuss.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
        this.fullscreen = useService("mail.fullscreen");
    },

    get showCallView() {
        return this.fullscreen.id !== CALL_FULLSCREEN && this.thread.rtc_session_ids.length > 0;
    },
});
