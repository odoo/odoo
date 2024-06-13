import { Component, onMounted, status, useRef } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { ErrorHandler, WithEnv } from "@web/core/utils/components";

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler, WithEnv };
    static props = { overlays: Object };

    setup() {
        this.root = useRef("root");
        // the first rendering ignores already registered overlays, it just renders the container
        // (see @isVisible) ; once mounted, the root ref is set, and we can render the overlays.
        onMounted(() => {
            if (this.props.overlays.length) {
                this.render();
            }
        });
    }

    get sortedOverlays() {
        return sortBy(Object.values(this.props.overlays), (overlay) => overlay.sequence);
    }

    isVisible(overlay) {
        return (
            status(this) === "mounted" && overlay.rootId === this.root.el.getRootNode()?.host?.id
        );
    }

    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
