import { useSubEnv } from "@web/owl2/utils";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";

import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { Component, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PortalChatter extends Component {
    static template = xml`
        <Chatter threadId="this.props.resId" threadModel="this.props.resModel" composer="this.props.composer" twoColumns="this.props.twoColumns"/>
        <div class="position-fixed" style="z-index:1030"><OverlayContainer overlays="this.overlayService.overlays"/></div>
    `;
    static components = { Chatter, OverlayContainer };
    static props = ["resId", "resModel", "composer", "twoColumns", "displayRating"];

    setup() {
        useSubEnv({
            displayRating: this.props.displayRating,
            inFrontendPortalChatter: true,
        });
        this.overlayService = useService("overlay");
    }
}
