/** @odoo-module **/

import { Component } from "@odoo/owl";
import { sortBy } from "../utils/arrays";
import { ErrorHandler } from "../utils/components";

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler };
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
