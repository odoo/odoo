import { useService } from "@web/core/utils/hooks";
import { Component, proxy } from "@odoo/owl";

export class MobilePreviewSystrayItem extends Component {
    static template = "website.MobilePreviewSystrayItem";
    static props = {};
    setup() {
        this.websiteService = useService("website");
        this.state = proxy(this.websiteService.context);
    }

    onClick() {
        this.websiteService.context.isMobile = !this.websiteService.context.isMobile;
    }
}
