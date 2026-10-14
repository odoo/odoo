import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { ChatHub } from "@mail/core/common/chat_hub";

import { Component, t, usePlugin, useProps, xml } from "@odoo/owl";
// overlay inside shadow so that the styles are dicted by the shadow dom
import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { useSubEnv } from "@web/owl2/utils";

export class LivechatRoot extends Component {
    static template = xml`
        <ChatHub/>
        <OverlayContainer/>
    `;
    static components = { ChatHub, LivechatButton, OverlayContainer };

    setup() {
        const rootId = useProps.static("rootId", t.any());
        useSubEnv({ rootId });
        useAncestors({ inLivechatRoot: true });
        this.overlayService = usePlugin(OverlayPlugin);
    }
}
