import { useAutoresize } from "@web/core/utils/autoresize";

import { Component, useRef } from "@odoo/owl";

export class PropertyText extends Component {
    static template = "web.PropertyText";
    static props = {
        updateProperty: Function,
        value: String,
    };

    setup() {
        this.textareaRef = useRef("textarea");
        useAutoresize(this.textareaRef);
    }
}
