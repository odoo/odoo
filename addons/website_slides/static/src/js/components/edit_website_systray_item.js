import { EditWebsiteSystrayItem } from "@website/client_actions/website_preview/edit_website_systray_item";
import { patch } from "@web/core/utils/patch";

patch(EditWebsiteSystrayItem.prototype, {
    isSlidePage() {
        const { pathname, search } = this.websiteService.contentWindow.location;
        return pathname.includes("slides") && search.includes("fullscreen=1");
    },
    getLocation() {
        if (this.isSlidePage()) {
            const location = this.websiteService.contentWindow.location;
            return {
                ...location,
                search: location.search.replace(/fullscreen=1/, "fullscreen=0"),
            };
        }
        return super.getLocation(...arguments);
    },

    onClickEditPage() {
        if (this.isSlidePage()) {
            const { pathname, search, hash } = this.getLocation();
            this.websiteService.goToWebsite({
                path: pathname + search + hash,
                edition: true,
            });
        }
        super.onClickEditPage(...arguments);
    },
});
