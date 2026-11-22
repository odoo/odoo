import { Message } from "@mail/core/common/message";
import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";

import { useMaybePlugin } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatterPlugin = useMaybePlugin(PortalChatterPlugin);
    },
});
