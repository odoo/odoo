import { discussSidebarChannelIndicatorsRegistry } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel";
import { propSignal } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DiscussSidebarCallIndicator extends Component {
    static template = "mail.DiscussSidebarCallIndicator";
    static components = {};

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.channel = propSignal("channel", t.instanceOf(this.store["discuss.channel"].Class));
        this.rtc = useService("discuss.rtc");
    }
}

discussSidebarChannelIndicatorsRegistry.add("call-indicator", DiscussSidebarCallIndicator);
