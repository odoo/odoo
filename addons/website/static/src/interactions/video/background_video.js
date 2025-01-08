import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";

export class BackgroundVideo extends Interaction {
    static selector = ".o_background_video";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _dropdown: () => this.el.closest(".dropdown-menu").parentElement,
        _modal: () => this.el.closest("modal"),
    };
    dynamicContent = {
        _document: {
            "t-on-optionalCookiesAccepted": () => this.iframeEl.src = this.videoSrc,
        },
        _window: {
            "t-on-resize": this.throttled(this.adjustIframe),
        },
        _dropdown: {
            "t-on-shown.bs.dropdown": this.throttled(this.adjustIframe),
        },
        _modal: {
            "t-on-show.bs.modal": () => this.hideVideoContainer = true,
            "t-on-shown.bs.modal": () => this.hideVideoContainer = false,
        },
        ".o_bg_video_container": {
            "t-att-class": () => ({
                "d-none": this.hideVideoContainer,
            }),
        },
    };

    setup() {
        this.hideVideoContainer = false;
        this.videoSrc = this.el.dataset.bgVideoSrc;
        this.iframeID = uniqueId("o_bg_video_iframe_");
        this.iframeEl = null;
        this.bgVideoContainer = null;
    }

    start() {
        const promise = setupAutoplay(this.videoSrc);
        if (promise) {
            this.videoSrc += "&enablejsapi=1";
            this.waitFor(promise).then(() => this.appendBgVideo());
        }
    }

    adjustIframe() {
        if (!this.iframeEl) {
            return;
        }

        this.iframeEl.classList.remove("show");

        var wrapperWidth = this.el.innerWidth;
        var wrapperHeight = this.el.innerHeight;
        var relativeRatio = (wrapperWidth / wrapperHeight) / (16 / 9);

        if (relativeRatio >= 1.0) {
            this.iframeEl.style.width = "100%";
            this.iframeEl.style.height = (relativeRatio * 100) + "%";
            this.iframeEl.style.insetInlineStart = "0";
            this.iframeEl.style.insetBlockStart = (-(relativeRatio - 1.0) / 2 * 100) + "%";
        } else {
            this.iframeEl.style.width = ((1 / relativeRatio) * 100) + "%";
            this.iframeEl.style.height = "100%";
            this.iframeEl.style.insetInlineStart = (-((1 / relativeRatio) - 1.0) / 2 * 100) + "%";
            this.iframeEl.style.insetBlockStart = "0";
        }

        void this.iframeEl.offsetWidth; // Force style addition
        this.iframeEl.classList.add("show");
    }

    appendBgVideo() {
        const allowedCookies = !this.el.dataset.needCookiesApproval;

        const oldContainer = this.bgVideoContainer || this.el.querySelector(":scope > .o_bg_video_container");
        this.bgVideoContainer = renderToElement("website.background.video", {
            videoSrc: allowedCookies ? this.videoSrc : "about:blank",
            iframeID: this.iframeID,
        });

        this.iframeEl = this.bgVideoContainer.querySelector(".o_bg_video_iframe");
        this.addListener(this.iframeEl, "load", () => {
            this.bgVideoContainer.querySelector(".o_bg_video_loading")?.remove();
            // When there is a "slide in (left or right) animation" element, we
            // need to adjust the iframe size once it has been loaded, otherwise
            // an horizontal scrollbar may appear.
            this.adjustIframe();
        });
        this.insert(this.bgVideoContainer, this.el, "afterbegin");
        oldContainer.remove();

        this.adjustIframe();
        triggerAutoplay(this.iframeEl);
    }
}

registry
    .category("public.interactions")
    .add("website.background_video", BackgroundVideo);

registry
    .category("public.interactions.edit")
    .add("website.background_video", {
        Interaction: BackgroundVideo,
    });
