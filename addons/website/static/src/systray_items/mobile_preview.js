/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState } = owl;

class MobilePreviewSystray extends Component {
    setup() {
        this.websiteService = useService('website');
        this.state = useState(this.websiteService.context);
    }
}
MobilePreviewSystray.template = "website.MobilePreviewSystray";

export const systrayItem = {
    Component: MobilePreviewSystray,
    isDisplayed: (env) => env.services.website.isRestrictedEditor,
};

registry.category("website_systray").add("MobilePreview", systrayItem, { sequence: 12 });
