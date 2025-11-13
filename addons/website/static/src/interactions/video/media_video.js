import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";
import { generateVideoIframe } from "@website/js/content/generate_video_iframe";

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

        // Generate the video `<iframe/>` element when restarting interacions.
        // In some cases (e.g., when adding a new video block), we don’t need
        // to rebuild the same iframe while starting the widget.
        if (!iframeEl) {
            iframeEl = generateVideoIframe(this.el, this.services.website_cookies.manageIframeSrc);
        }

        if (iframeEl && !iframeEl.getAttribute("aria-label")) {
            iframeEl.setAttribute("aria-label", _t("Media video"));
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
}

registry.category("public.interactions").add("website.media_video", MediaVideo);
