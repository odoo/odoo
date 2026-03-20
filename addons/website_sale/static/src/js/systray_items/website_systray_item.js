import { patch } from '@web/core/utils/patch';
import { WebsiteSystrayItem } from '@website/client_actions/website_preview/website_systray_item';

patch(WebsiteSystrayItem.prototype, {
    get canPublish() {
        const mainObject = this.website.currentWebsite.metadata.mainObject;

        return mainObject?.model === 'product.public.category'
            ? false
            : super.canPublish;
    },
});
