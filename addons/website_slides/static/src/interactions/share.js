import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { SlideShareDialog } from '../js/public/components/slide_share_dialog/slide_share_dialog';

export class Share extends Interaction {
    static selector = ".o_wslides_share";
    dynamicContent = {
        _root: { "t-on-click.prevent.stop.withTarget": this.onClick },
    }

    getDocumentMaxPage() {
        const iframe = document.querySelector("iframe.o_wslides_iframe_viewer");
        const iframeDocument = iframe.contentWindow.document;
        return parseInt(iframeDocument.querySelector("#page_count").innerText);
    }

    onClick(ev, currentTargetEl) {
        const data = currentTargetEl.dataset;
        this.services.dialog.add(SlideShareDialog, {
            category: data.category,
            documentMaxPage: data.category == 'document' && this.getDocumentMaxPage(),
            emailSharing: data.emailSharing === 'True',
            embedCode: data.embedCode,
            id: parseInt(data.id),
            isChannel: data.isChannel === 'True',
            name: data.name,
            url: data.url,
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.share", Share);
