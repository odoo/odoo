import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";

import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { Component, plugin, providePlugins, useSubEnv, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PortalChatter extends Component {
    static template = xml`
        <Chatter threadId="this.props.resId" threadModel="this.props.resModel" composer="this.props.composer" twoColumns="this.props.twoColumns"/>
        <div class="position-fixed o-portal-overlay"><OverlayContainer overlays="this.overlayService.overlays"/></div>
    `;
    static components = { Chatter, OverlayContainer };
    static props = ["resId", "resModel", "composer", "twoColumns", "displayRating", "reviewChatter?"];

    setup() {
        providePlugins([PortalChatterPlugin]);
        const portalChatterPlugin = plugin(PortalChatterPlugin);
        portalChatterPlugin.displayRating.set(this.props.displayRating);
        portalChatterPlugin.inFrontendPortalChatter.set(true);
        useSubEnv({ inFrontendPortalChatter: true });
        this.overlayService = useService("overlay");
        this.store = useService("mail.store");
        this.env.bus.addEventListener("reload_chatter_content", (ev) =>
            this._reloadChatterContent(ev.detail)
        );
    }

    async _reloadChatterContent() {
        const thread = this.store["mail.thread"].get({
            id: this.props.resId,
            model: this.props.resModel,
        });
        await (thread._reloadReviews?.() ?? thread.fetchNewMessages());
    }
}
