import { Component, t, useProps, xml } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/** Selection of the status of a livechat, as a panel of its status action. */
export class LivechatStatusSelection extends Component {
    /** @see PanelDefinition: a list of choices, opening in a dropdown of its action by default */
    static menu = true;
    static template = xml`
        <t t-call="im_livechat.LivechatStatusSelection" templateParams="{ livechatThread: this.props.thread }"/>
    `;
    props = useProps({ close: t.function().optional(), thread: t.object() });

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
}
