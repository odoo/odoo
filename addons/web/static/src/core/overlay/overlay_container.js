import { Component, useRef } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { ErrorHandler, WithEnv } from "@web/core/utils/components";

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler, WithEnv };
    static props = { overlays: Object };

    setup() {
        this.root = useRef("root");
    }

    get sortedOverlays() {
        return sortBy(Object.values(this.props.overlays), (overlay) => overlay.sequence);
    }

    isVisible(overlay) {
        return overlay.rootId === this.root.el?.getRootNode()?.host?.id;
    }

    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
