import { useAutoresize } from "@web/core/utils/autoresize";

import { Component, signal } from "@odoo/owl";

export class PropertyText extends Component {
    static template = "web.PropertyText";
    static props = {
        updateProperty: Function,
        value: String,
    };

    textareaRef = signal(null);

    setup() {
        useAutoresize(this.textareaRef);
    }
}
