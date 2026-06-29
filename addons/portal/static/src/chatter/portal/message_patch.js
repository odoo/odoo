import { Message } from "@mail/core/common/message";
import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { maybePlugin } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatterPlugin = maybePlugin(PortalChatterPlugin);
    },
});
