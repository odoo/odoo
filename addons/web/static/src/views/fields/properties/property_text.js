import { useAutoresize } from "@web/core/utils/autoresize";

import { Component, signal, t, useProps } from "@odoo/owl";

export class PropertyText extends Component {
    static template = "web.PropertyText";
    props = useProps({
        updateProperty: t.function(),
        value: t.string(),
    });

    textareaRef = signal(null);

    setup() {
        useAutoresize(this.textareaRef);
    }
}
