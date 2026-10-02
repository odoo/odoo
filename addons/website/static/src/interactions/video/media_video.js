import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";
import { generateVideoPlayer } from "@website/js/content/generate_video_iframe";

export class MediaVideo extends Interaction {
    static selector = ".media_iframe_video";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _popup: () => this.el.closest(".s_popup"),
    };
    dynamicContent = {
        _popup: {
            "t-on-shown.bs.modal": () => {
                const iframeEl = this.el.querySelector("iframe");
                if (!iframeEl) {
                    return;
                }
                this.services.website_cookies.manageIframeSrc(iframeEl, this.iframeSrc);
            },
            "t-on-hide.bs.modal": () => {
                const iframeEl = this.el.querySelector("iframe");
                if (!iframeEl) {
                    return;
                }
                iframeEl.src = "";
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
        let playerEl = this.el.querySelector(":scope > :is(iframe, video)");

        // Generate the video player element when restarting interacions.
        // In some cases (e.g., when adding a new video block), we don’t need
        // to rebuild the same player while starting the widget.
        if (!playerEl) {
            playerEl = generateVideoPlayer(this.el, this.services.website_cookies.manageIframeSrc);
        }

        this.iframeSrc = playerEl?.dataset.nocookieSrc || playerEl?.getAttribute("src") || "";

        if (playerEl && !playerEl.getAttribute("aria-label")) {
            playerEl.setAttribute("aria-label", _t("Media video"));
        }

        if (playerEl?.tagName === "VIDEO") {
            return;
        }

        if (playerEl?.hasAttribute("src")) {
            const promise = setupAutoplay(
                playerEl.getAttribute("src"),
                !!this.el.dataset.needCookiesApproval
            );
            if (promise) {
                this.waitFor(promise).then(
                    this.protectSyncAfterAsync(() => triggerAutoplay(playerEl))
                );
            }
        }
    }
}

registry.category("public.interactions").add("website.media_video", MediaVideo);
