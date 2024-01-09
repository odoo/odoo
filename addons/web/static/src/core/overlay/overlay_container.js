import { Component } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { ErrorHandler, WithEnv } from "@web/core/utils/components";

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler, WithEnv };
    static props = { overlays: Object };

    get sortedOverlays() {
        return sortBy(Object.values(this.props.overlays), (overlay) => overlay.sequence);
    }

    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
