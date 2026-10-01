import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { ChatHub } from "@mail/core/common/chat_hub";

import { Component, usePlugin, xml } from "@odoo/owl";
// overlay inside shadow so that the styles are dicted by the shadow dom
import { OverlayContainer } from "@web/core/overlay/overlay_container";

export class LivechatRoot extends Component {
    static template = xml`
        <ChatHub/>
        <OverlayContainer/>
    `;
    static components = { ChatHub, LivechatButton, OverlayContainer };

    setup() {
        useAncestors({ inLivechatRoot: true });
        this.overlayService = usePlugin(OverlayPlugin);
    }
}
