import { htmlEscape } from "@odoo/owl";

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";

export class MediaVideo extends Interaction {
    static selector = ".media_iframe_video";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _popup: () => this.el.closest(".s_popup"),
    };
    dynamicContent = {
        _popup: {
            "t-on-shown.bs.modal": () => {
                // TODO still oeExpression to remove someday
                this.services.website_cookies.manageIframeSrc(
                    this.el.querySelector("iframe"),
                    this.el.dataset.oeExpression || this.el.dataset.src
                );
            },
            "t-on-hide.bs.modal": () => {
                this.el.querySelector("iframe").src = "";
            },
        },
        _document: {
            "t-on-optionalCookiesAccepted": () => {
                this.cookiesAccepted = true;
            },
        },
        ":scope > .media_iframe_video_size": {
            "t-att-class": () => ({ "d-none": !this.cookiesAccepted }),
        },
    };

    setup() {
        this.cookiesAccepted = this.el.dataset.needCookiesApproval !== "true";
    }

    start() {
        let iframeEl = this.el.querySelector(":scope > iframe");

        // The following code is only there to ensure compatibility with
        // videos added before bug fixes or new Odoo versions where the
        // <iframe/> element is properly saved.
        if (!iframeEl) {
            iframeEl = this.generateIframe();
        }

        if (iframeEl?.hasAttribute("src")) {
            const promise = setupAutoplay(
                iframeEl.getAttribute("src"),
                !!this.el.dataset.needCookiesApproval
            );
            if (promise) {
                this.waitFor(promise).then(
                    this.protectSyncAfterAsync(() => triggerAutoplay(iframeEl))
                );
            }
        }
    }

    generateIframe() {
        // Bug fix / compatibility: empty the <div/> element as all information
        // to rebuild the iframe should have been saved on the <div/> element
        this.el.textContent = "";

        // Add extra content for size / edition
        const div1 = document.createElement("div");
        div1.classList.add("css_editable_mode_display");
        div1.innerHTML = "&nbsp;";
        const div2 = document.createElement("div");
        div2.classList.add("media_iframe_video_size");
        div2.innerHTML = "&nbsp;";
        this.insert(div1);
        this.insert(div2);

        // Rebuild the iframe. Depending on version / compatibility / instance,
        // the src is saved in the 'data-src' attribute or the
        // 'data-oe-expression' one (the latter is used as a workaround in 10.0
        // system but should obviously be reviewed in master).

        const src = htmlEscape(
            this.el.getAttribute("data-oe-expression") || this.el.getAttribute("data-src")
        );
        // Validate the src to only accept supported domains we can trust

        const m = src.match(/^(?:https?:)?\/\/([^/?#]+)/);
        if (!m) {
            return;
        }

        const domain = m[1].replace(/^www\./, "");
        const supportedDomains = [
            "youtu.be",
            "youtube.com",
            "youtube-nocookie.com",
            "instagram.com",
            "player.vimeo.com",
            "vimeo.com",
            "dailymotion.com",
        ];
        if (!supportedDomains.includes(domain)) {
            return;
        }

        const iframeEl = document.createElement("iframe");
        iframeEl.frameborder = "0";
        iframeEl.allowFullscreen = "allowfullscreen";
        iframeEl.ariaLabel = _t("Media video");
        this.insert(iframeEl);
        this.services.website_cookies.manageIframeSrc(iframeEl, src);
        return iframeEl;
    }
}

registry.category("public.interactions").add("website.media_video", MediaVideo);
