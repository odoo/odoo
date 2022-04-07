/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class MobilePreviewSystray extends Component {
    setup() {
        this.websiteService = useService('website');
    }
}
MobilePreviewSystray.template = "website.MobilePreviewSystray";

export const systrayItem = {
    Component: MobilePreviewSystray,
};

registry.category("website_systray").add("MobilePreview", systrayItem, { sequence: 12 });
