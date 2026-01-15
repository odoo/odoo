import { ChatWindow } from "@mail/core/common/chat_window";
import { Call } from "@mail/discuss/call/common/call";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";
import { useService } from "@web/core/utils/hooks";

import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { Call, PipBanner });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
    },
});
