/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OverlayContainer } from "@web/core/overlay/overlay_container";

patch(OverlayContainer.prototype, {
    isVisible(overlay) {
        const targetRoot = overlay.props.target?.getRootNode();
        const targetInShadow =
            targetRoot instanceof ShadowRoot && targetRoot.host.id === this.env.shadowRootId;
        return targetInShadow ? this.env.inShadow : !this.env.inShadow;
    },
});
