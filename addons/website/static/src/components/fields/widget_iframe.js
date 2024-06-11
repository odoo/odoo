/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useBus } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class FieldIframePreview extends Component {
    setup() {
        this.state = useState({isMobile: false});

        useBus(this.env.bus, 'THEME_PREVIEW:SWITCH_MODE', (ev) => {
            this.state.isMobile = ev.detail.mode === 'mobile';
        });
    }
}
FieldIframePreview.template = 'website.iframeWidget';

export const fieldIframePreview = {
    component: FieldIframePreview,
};

registry.category("fields").add("iframe", fieldIframePreview);
