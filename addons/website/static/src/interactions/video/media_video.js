/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { Interaction } from "@web/public/interaction";
import {
    generateVideoIframe,
    isVideoInClosedPopup,
} from "@website/js/content/generate_video_iframe";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";

const log = makeLogger("website.interaction.media_video");

export class MediaVideo extends Interaction {
    static selector = ".media_iframe_video";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _popup: () => this.el.closest(".s_popup"),
    };
    dynamicContent = {
        _popup: {
            "t-on-shown.bs.modal": () => {
                this.popupOpenVersion++;
                if (!this.iframeEl) {
                    return;
                }
                this.services.website_cookies.manageIframeSrc(
                    this.iframeEl,
                    this.el.dataset.oeExpression || this.el.dataset.src,
                );
                this.activateAutoplay();
            },
            "t-on-hide.bs.modal": (event) => {
                const version = this.popupOpenVersion;
                // A later listener can cancel this close during bubbling.
                this.waitFor().then(
                    this.bindDeferred(() => {
                        if (
                            event.defaultPrevented ||
                            version !== this.popupOpenVersion
                        ) {
                            log.lifecycle("MediaVideo close cancelled or superseded");
                            return;
                        }
                        this.autoplayRequest = null;
                        if (this.iframeEl) {
                            // Opening restores the configured source through the service.
                            delete this.iframeEl.dataset.nocookieSrc;
                            this.iframeEl.src = "";
                            log.lifecycle(
                                "MediaVideo popup closed: discard pending source",
                            );
                        }
                    }),
                );
            },
        },
        _document: {
            "t-on-optionalCookiesAccepted.once": () => {
                if (this.cookiesAccepted) {
                    return;
                }
                this.cookiesAccepted = true;
                // Cookie interactions restore URLs during the same dispatch.
                this.waitFor().then(this.bindDeferred(this.activateAutoplay));
            },
        },
        ":scope > .media_iframe_video_size": {
            "t-att-class": () => ({ "d-none": !this.cookiesAccepted }),
        },
    };

    /** @returns {HTMLIFrameElement | null} */
    get iframeEl() {
        return this.el.querySelector(":scope > iframe");
    }

    setup() {
        this.popupOpenVersion = 0;
        this.cookiesAccepted = !this.el.closest("[data-need-cookies-approval]");
        log.lifecycle("MediaVideo setup", () => ({
            cookiesAccepted: this.cookiesAccepted,
        }));
    }

    start() {
        let iframeEl = this.el.querySelector(":scope > iframe");

        if (!iframeEl) {
            iframeEl = generateVideoIframe(
                this.el,
                this.services.website_cookies.manageIframeSrc,
            );
            log.logic("MediaVideo start: generated iframe", () => ({
                generated: !!iframeEl,
                src: this.el.dataset.oeExpression || this.el.dataset.src,
            }));
        }

        if (iframeEl && !iframeEl.getAttribute("aria-label")) {
            iframeEl.setAttribute("aria-label", _t("Media video"));
        }

        this.cookiesAccepted = !(iframeEl || this.el).closest(
            "[data-need-cookies-approval]",
        );
        if (iframeEl && isVideoInClosedPopup(this.el)) {
            delete iframeEl.dataset.nocookieSrc;
            iframeEl.setAttribute("src", "about:blank");
            log.lifecycle("MediaVideo start: wait for popup opening");
            return;
        }
        this.activateAutoplay();
    }

    activateAutoplay() {
        const iframe = this.iframeEl;
        const src = iframe?.getAttribute("src");
        if (!src) {
            return;
        }
        const request = {};
        this.autoplayRequest = request;
        const needsApproval = !!iframe.closest("[data-need-cookies-approval]");
        log.logic("MediaVideo autoplay setup", () => ({ needsApproval, src }));
        const canPlay = () =>
            !this.isDestroyed &&
            this.autoplayRequest === request &&
            iframe === this.iframeEl;
        this.waitFor(setupAutoplay(src, needsApproval)).then(
            this.bindDeferred(() => {
                if (canPlay() && iframe.getAttribute("src") === src) {
                    triggerAutoplay(iframe, canPlay);
                }
            }),
        );
    }
}

registry.category("public.interactions").add("website.media_video", MediaVideo);
