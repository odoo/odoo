import { patch } from "@web/core/utils/patch";
import { LinkPopover } from "@html_editor/main/link/link_popover";

patch(LinkPopover.prototype, {
    isLogoutUrl() {
        return (
            !!this.state.url.match(/\/hr_attendance\/kiosk_mode_menu\/\d+/) ||
            !!this.state.url.match(/\/hr_attendance\/[0-9a-f]{32}/) ||
            !!this.state.url.match(/\/hr_attendance\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}/) ||
            super.isLogoutUrl()
        );
    }
})
