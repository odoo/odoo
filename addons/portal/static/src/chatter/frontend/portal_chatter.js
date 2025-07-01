import { Chatter } from "@mail/chatter/web_portal/chatter";

import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { Component, xml, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PortalChatter extends Component {
    static template = xml`
        <Chatter threadId="props.resId" threadModel="props.resModel" composer="props.composer" twoColumns="props.twoColumns"/>
        <div class="position-fixed" style="z-index:1030"><OverlayContainer overlays="overlayService.overlays"/></div>
    `;
    static components = { Chatter, OverlayContainer };
    static props = ["resId", "resModel", "composer", "twoColumns", "displayRating"];

    setup() {
        useSubEnv({
            displayRating: this.props.displayRating,
            inFrontendPortalChatter: true,
        });
        this.overlayService = useService("overlay");
        this.store = useService("mail.store");
        this.env.bus.addEventListener("reload_chatter_content", (ev) =>
            this._reloadChatterContent(ev.detail)
        );
    }

    async _reloadChatterContent(data) {
        const thread = this.store.Thread.get({
            id: this.props.resId,
            model: this.props.resModel,
        });
        thread.messages = await thread.fetchMessages();
    }
}
