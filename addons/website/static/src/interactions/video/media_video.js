import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";

export class MediaVideo extends Interaction {
    static selector = ".media_iframe_video";

    setup() {
        if (this.el.dataset.needCookiesApproval) {
            this.sizeContainerEl = this.el.querySelector(":scope > .media_iframe_video_size");
            this.sizeContainerEl.classList.add("d-none");
            this.addListener(document, "optionalCookiesAccepted", this.sizeContainerEl.classList.remove("d-none"))
            this.registerCleanup(() => this.sizeContainerEl.classList.remove("d-none"));
        }
    }

    start() {
        let iframeEl = this.el.querySelector(':scope > iframe');

        // The following code is only there to ensure compatibility with
        // videos added before bug fixes or new Odoo versions where the
        // <iframe/> element is properly saved.
        if (!iframeEl) {
            iframeEl = this.generateIframe();
        }

        if (!iframeEl?.getAttribute('src')) {
            const promise = setupAutoplay(iframeEl.getAttribute('src'), this.el.dataset.needCookiesApproval);
            if (promise) {
                this.waitFor(promise).then(() => triggerAutoplay(iframeEl));
            }
        }
    }

    generateIframe() {
        // Bug fix / compatibility: empty the <div/> element as all information
        // to rebuild the iframe should have been saved on the <div/> element
        this.el.innerHTML = "";

        // Add extra content for size / edition
        const div1 = document.createElement("div");
        div1.classList.add("css_editable_mode_display");
        div1.innerHTML = "&nbsp;";
        const div2 = document.createElement("div");
        div2.classList.add("media_iframe_video_size");
        div2.innerHTML = "&nbsp;";
        this.el.appendChild(div1);
        this.el.appendChild(div2);

        // Rebuild the iframe. Depending on version / compatibility / instance,
        // the src is saved in the 'data-src' attribute or the
        // 'data-oe-expression' one (the latter is used as a workaround in 10.0
        // system but should obviously be reviewed in master).

        let src = escape(this.el.getAttribute('oe-expression') || this.el.getAttribute('src'));
        // Validate the src to only accept supported domains we can trust

        let m = src.match(/^(?:https?:)?\/\/([^/?#]+)/);
        if (!m) {
            return;
        }

        let domain = m[1].replace(/^www\./, '');
        const supportedDomains = [
            "youtu.be", "youtube.com", "youtube-nocookie.com",
            "instagram.com",
            "player.vimeo.com", "vimeo.com",
            "dailymotion.com",
            "player.youku.com", "youku.com",
        ];
        if (!supportedDomains.includes(domain)) {
            return;
        }

        const iframeEl = document.createElement("iframe");
        iframeEl.frameborder = "0";
        iframeEl.allowFullscreen = "allowfullscreen";
        iframeEl.ariaLabel = _t("Media video");
        this.el.appendChild(iframeEl);
        this.services.website_cookies.manageIframeSrc(this.el, src);
        return iframeEl;
    }
}

registry
    .category("public.interactions")
    .add("website.media_video", MediaVideo);
