import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { SlideShareDialog } from '../js/public/components/slide_share_dialog/slide_share_dialog';

export class Share extends Interaction {
    static selector = ".o_wslides_share";
    dynamicContent = {
        _root: { "t-on-click.prevent.stop.withTarget": this.onClick },
    }

    setup() {
        if (this.isFullscreen()) {
            this.slidesService = this.services.website_slides;
            this.slide = this.slidesService.data.slide;
        }
    }

    isFullscreen() {
        return document.querySelector('.o_wslides_fs_main');
    }

    getDocumentMaxPage() {
        const iframe = document.querySelector("iframe.o_wslides_iframe_viewer");
        const iframeDocument = iframe.contentWindow.document;
        return parseInt(iframeDocument.querySelector("#page_count").innerText);
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    onClick(ev, currentTargetEl) {
        const slide = this.isFullscreen() ? this.slide : currentTargetEl.dataset;
        const isDocumentSlide = slide.category === "document";
        const embedUrl = isDocumentSlide && slide.embedCode ? 
            this.isFullscreen() ? slide.embedUrl : slide.embedCode.slice(
                slide.embedCode.indexOf('src="') + 5,
                slide.embedCode.indexOf('"', slide.embedCode.indexOf('src="') + 5)
            )
            : undefined;
        this.services.dialog.add(SlideShareDialog, {
            category: slide.category,
            documentMaxPage:
                isDocumentSlide &&
                embedUrl &&
                new URL(embedUrl, window.location.href).origin === window.location.origin &&
                this.getDocumentMaxPage(),
            emailSharing: slide.emailSharing || slide.emailSharing === 'True',
            embedCode: slide.embedCode || "",
            id: parseInt(slide.id),
            isChannel: slide.isChannel === 'True',
            name: slide.name,
            url: slide.websiteShareUrl || slide.url,
            ...(this.isFullscreen() && { isFullscreen: true })
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.share", Share);
