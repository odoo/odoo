import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

import { ChatHub } from "@mail/core/common/chat_hub";

import { Component, useSubEnv, xml } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
// overlay inside shadow so that the styles are dicted by the shadow dom
import { OverlayContainer } from "@web/core/overlay/overlay_container";

export class LivechatRoot extends Component {
    static template = xml`
        <ChatHub/>
        <LivechatButton/>
        <OverlayContainer overlays="overlayService.overlays"/>
    `;
    static components = { ChatHub, LivechatButton, OverlayContainer };
    static props = {};

    setup() {
        useSubEnv({ embedLivechat: true });
        this.overlayService = useService("overlay");
    }
}
