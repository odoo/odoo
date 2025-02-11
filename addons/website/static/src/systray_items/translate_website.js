/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from '@web/core/utils/hooks';
import { Component, useState } from "@odoo/owl";

class TranslateWebsiteSystray extends Component {
    setup() {
        this.rpc = useService("rpc"),
        this.websiteService = useService('website');
        this.websiteContext = useState(this.websiteService.context);
    }

    attemptStartTranslate() {
        if (this.websiteService.isRestrictedEditor && !this.websiteService.isDesigner) {
            if (!this.websiteService.websiteRootInstance) {
                // Root instance might not be there yet if user clicks too fast.
                // Let's have him click again rather than apply different rules.
                return;
            }
            const object = this.websiteService.currentWebsite.metadata.mainObject;
            const objects = {
                [object.model]: object.id,
            };
            const otherRecordEls = this.websiteService.websiteRootInstance.el.querySelectorAll(
                "[data-res-model][data-res-id]:not([data-res-model='ir.ui.view']), [data-oe-model][data-oe-id]:not([data-oe-model='ir.ui.view'])"
            );
            for (const el of otherRecordEls) {
                const model = el.dataset.resModel || el.dataset.oeModel;
                if (!objects[model]) {
                    // Keep one record of each type.
                    objects[model] = parseInt(el.dataset.resId || el.dataset.oeId);
                }
            }
            this.rpc('/website/check_can_modify_any', {
                records: Object.entries(objects).map((kv) => {
                    return {
                        res_model: kv[0],
                        res_id: kv[1],
                    };
                }),
            }).then(() => {
                this.startTranslate();
            });
        } else {
            this.startTranslate();
        }
    }

    startTranslate() {
        const { pathname, search, hash } = this.websiteService.contentWindow.location;
        if (!search.includes('edit_translations')) {
            const searchParams = new URLSearchParams(search);
            searchParams.set('edit_translations', '1');
            this.websiteService.goToWebsite({
                path: pathname + `?${searchParams.toString() + hash}`,
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

registry.category("website_systray").add("TranslateWebsiteSystray", systrayItem, { sequence: 8 });
