/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class MobilePreviewSystray extends Component {
    static template = "website.MobilePreviewSystray";
    static props = {};
    setup() {
        this.websiteService = useService('website');
        this.state = useState(this.websiteService.context);
    }
}

export const systrayItem = {
    Component: MobilePreviewSystray,
};

registry.category("website_systray").add("MobilePreview", systrayItem, { sequence: 11 });
