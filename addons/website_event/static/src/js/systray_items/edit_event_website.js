import { EditWebsiteSystray } from '@website/systray_items/edit_website';
import { patch } from "@web/core/utils/patch";
import { useService } from '@web/core/utils/hooks';

patch(EditWebsiteSystray.prototype, {

    setup() {
        super.setup();
        this.http = useService("http");
    },

    async createPage() {
        if (this.websiteService.currentWebsite.metadata.viewXmlid === "website_event.page_404") {
            const pageName = this.websiteService.currentLocation.split('/page/')[1];
            const eventPage = await this.http.post(`/website/add/${pageName}`, {
                template: "website_event.default_page",
                event_url: this.websiteService.currentLocation,
                website_id: this.websiteService.currentWebsite.id,
                csrf_token: odoo.csrf_token,
            });
            this.websiteService.goToWebsite({
                path: eventPage.url,
                edition: true,
                websiteId: this.websiteService.currentWebsite.id
            });
        } else {
            super.createPage();
        }
    },
});
