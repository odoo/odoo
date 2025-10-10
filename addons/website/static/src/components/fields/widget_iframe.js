import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class FieldIframePreview extends Component {
    static template = "website.iframeWidget";
    static props = { ...standardFieldProps };
    setup() {
        this.state = useState({ isMobile: false });

        useBus(this.env.bus, "THEME_PREVIEW:SWITCH_MODE", (ev) => {
            this.state.isMobile = ev.detail.mode === "mobile";
        });
    }
}

export const fieldIframePreview = {
    component: FieldIframePreview,
};

registry.category("fields").add("iframe", fieldIframePreview);
