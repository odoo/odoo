import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { useSubEnv } from "@web/owl2/utils";
import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";

import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { Component, providePlugins, t, useListener, usePlugin, useProps, xml } from "@odoo/owl";

export class PortalChatter extends Component {
    static template = xml`
        <Chatter threadId="this.props.resId" threadModel="this.props.resModel" composer="this.props.composer" twoColumns="this.props.twoColumns"/>
        <div class="position-fixed o-portal-overlay"><OverlayContainer/></div>
    `;
    static components = { Chatter, OverlayContainer };
    props = useProps({
        resId: t.any(),
        resModel: t.any(),
        composer: t.any(),
        twoColumns: t.any(),
        displayRating: t.any(),
        reviewChatter: t.any().optional(),
    });

    setup() {
        providePlugins([PortalChatterPlugin]);
        const portalChatterPlugin = usePlugin(PortalChatterPlugin);
        portalChatterPlugin.displayRating.set(this.props.displayRating);
        useSubEnv({ inFrontendPortalChatter: true });
        this.overlayService = usePlugin(OverlayPlugin);
        useListener(this.env.bus, "reload_chatter_content", () =>
            this.env.bus.trigger("MAIL:RELOAD-THREAD", {
                id: this.props.resId,
                model: this.props.resModel,
            })
        );
    }
}
