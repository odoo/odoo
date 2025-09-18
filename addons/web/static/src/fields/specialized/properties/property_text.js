// @ts-check

/** @module @web/fields/specialized/properties/property_text - Auto-resizing textarea component for property text values */

import { Component, useRef } from "@odoo/owl";
import { useAutoresize } from "@web/core/utils/dom/autoresize";
export class PropertyText extends Component {
    static template = "web.PropertyText";
    static props = {
        updateProperty: Function,
        value: String,
    };

    setup() {
        this.textareaRef = useRef("textarea");
        useAutoresize(/** @type {any} */ (this.textareaRef));
    }
}
