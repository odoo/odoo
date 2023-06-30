/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OverlayContainer } from "@web/core/overlay/overlay_container";

patch(OverlayContainer.prototype, "im_livechat", {
    isVisible(overlay) {
        const targetInShadow = overlay.props.target?.getRootNode() instanceof ShadowRoot;
        return targetInShadow ? this.env.inShadow : !this.env.inShadow;
    }
});
