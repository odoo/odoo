/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { sortBy } from "../utils/arrays";
import { ErrorHandler } from "../utils/components";
import { useService } from "../utils/hooks";

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler };
    static props = {};

    setup() {
        this.overlays = useState(useService("overlay").overlays);
    }

    get sortedOverlays() {
        return sortBy(Object.values(this.overlays), (overlay) => overlay.sequence);
    }

    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
