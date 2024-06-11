/* @odoo-module */

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

import { ChatWindowContainer } from "@mail/core/common/chat_window_container";

import { Component, xml, useSubEnv } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
// overlay inside shadow so that the styles are dicted by the shadow dom
import { OverlayContainer } from "@web/core/overlay/overlay_container";

export class LivechatRoot extends Component {
    static template = xml`
        <ChatWindowContainer/>
        <LivechatButton/>
        <OverlayContainer overlays="overlayService.overlays"/>
    `;
    static components = { ChatWindowContainer, LivechatButton, OverlayContainer };

    setup() {
        useSubEnv({ inShadow: true });
        this.overlayService = useService("overlay");
    }
}
