/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from '@web/core/utils/hooks';

const { Component, useState } = owl;

class TranslateWebsiteSystray extends Component {
    setup() {
        this.websiteService = useService('website');
        this.websiteContext = useState(this.websiteService.context);
    }

    startTranslate() {
        const { pathname, search, hash } = this.websiteService.contentWindow.location;
        if (!search.includes('edit_translations')) {
            const searchParams = new URLSearchParams(search);
            searchParams.set('edit_translations', '1');
            this.websiteService.goToWebsite({
                path: encodeURI(pathname + `?${searchParams.toString() + hash}`),
                translation: true
            });
        } else {
            this.websiteContext.translation = true;
        }
    }
}
TranslateWebsiteSystray.template = "website.TranslateWebsiteSystray";

export const systrayItem = {
    Component: TranslateWebsiteSystray,
    isDisplayed: env => env.services.website.currentWebsite && env.services.website.currentWebsite.metadata.translatable,
};

registry.category("website_systray").add("TranslateWebsiteSystray", systrayItem, { sequence: 9 });
