import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";

export class BackgroundVideo extends Interaction {
    static selector = ".o_background_video";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _dropdown: () => this.el.closest(".dropdown-menu")?.parentElement,
        _modal: () => this.el.closest("modal"),
    };
    dynamicContent = {
        _document: {
            // We don't add the optional cookies warning for background videos
            // so that the fallback message doesn't appear behind the content.
            "t-on-optionalCookiesAccepted.once": () => {
                if (!this.isVideoFile) {
                    this.playerEl.src = this.videoSrc;
                }
            },
        },
        _window: {
            "t-on-resize": this.throttled(this.adjustPlayer),
        },
        _dropdown: {
            "t-on-shown.bs.dropdown": this.throttled(this.adjustPlayer),
        },
        _modal: {
            "t-on-show.bs.modal": () => (this.hideVideoContainer = true),
            "t-on-shown.bs.modal": () => (this.hideVideoContainer = false),
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
        this.isVideoFile = "bgVideoIsFile" in this.el.dataset;
        this.iframeID = uniqueId("o_bg_video_iframe_");
        this.playerEl = null;
        this.bgVideoContainer = null;
    }

    start() {
        const promise = setupAutoplay(this.videoSrc, !!this.el.dataset.needCookiesApproval);
        if (promise) {
            this.waitFor(promise).then(this.protectSyncAfterAsync(this.appendBgVideo));
        }
        this.__adjustPlayer = this.throttled(this.adjustPlayer);
        const resizeObserver = new ResizeObserver(this.__adjustPlayer.bind(this));
        // A change in an element padding does not trigger the resizeObserver so
        // both inner and outer element are observed for any resizing.
        resizeObserver.observe(this.el.parentElement);
        resizeObserver.observe(this.el);
    }

    adjustPlayer() {
        if (!this.playerEl) {
            return;
        }
        if (this.isVideoFile) {
            // A `<video>` element covers its container on its own, through
            // `object-fit`, so it needs no manual sizing.
            this.playerEl.classList.add("show");
            return;
        }

        this.playerEl.classList.remove("show");

        const wrapperWidth = this.el.clientWidth;
        const wrapperHeight = this.el.clientHeight;
        const relativeRatio = wrapperWidth / wrapperHeight / (16 / 9);

        if (this.el.closest(".s_ecomm_categories_showcase_block")) {
            // Chrome-only: percentage sizing makes the video in "Categories
            // Showcase" snippet jitter on hover, so force pixel values while
            // keeping the ratio.
            const iframeHeight = Math.round(
                relativeRatio >= 1 ? wrapperWidth * (9 / 16) : wrapperHeight
            );
            const iframeWidth = Math.round(
                relativeRatio >= 1 ? wrapperWidth : wrapperHeight * (16 / 9)
            );
            this.playerEl.style.height = `${iframeHeight}px`;
            this.playerEl.style.width = `${iframeWidth}px`;
        } else if (relativeRatio >= 1.0) {
            this.playerEl.style.width = "100%";
            this.playerEl.style.height = relativeRatio * 100 + "%";
            this.playerEl.style.insetInlineStart = "0";
            this.playerEl.style.insetBlockStart = (-(relativeRatio - 1.0) / 2) * 100 + "%";
        } else {
            this.playerEl.style.width = (1 / relativeRatio) * 100 + "%";
            this.playerEl.style.height = "100%";
            this.playerEl.style.insetInlineStart = (-(1 / relativeRatio - 1.0) / 2) * 100 + "%";
            this.playerEl.style.insetBlockStart = "0";
        }

        void this.playerEl.offsetWidth; // Force style addition
        this.playerEl.classList.add("show");
    }

    appendBgVideo() {
        const allowedCookies = !this.el.dataset.needCookiesApproval;

        const oldContainer =
            this.bgVideoContainer || this.el.querySelector(":scope > .o_bg_video_container");
        oldContainer?.remove();

        this.renderAt(
            "website.background.video",
            {
                videoSrc: allowedCookies || this.isVideoFile ? this.videoSrc : "about:blank",
                iframeID: this.iframeID,
                isVideoFile: this.isVideoFile,
            },
            this.el,
            "afterbegin"
        );

        this.bgVideoContainer = this.el.querySelector(":scope > .o_bg_video_container");
        this.playerEl = this.bgVideoContainer.querySelector(".o_bg_video_iframe, .o_bg_video_file");
        this.addListener(
            this.playerEl,
            this.isVideoFile ? "loadeddata" : "load",
            () => {
                this.bgVideoContainer.querySelector(".o_bg_video_loading")?.remove();
                // When there is a "slide in (left or right) animation" element,
                // we need to adjust the player size once it has been loaded,
                // otherwise an horizontal scrollbar may appear.
                this.adjustPlayer();
            },
            { once: true }
        );

        this.adjustPlayer();
        triggerAutoplay(this.playerEl);
    }
}

registry.category("public.interactions").add("website.background_video", BackgroundVideo);

registry.category("public.interactions.edit").add("website.background_video", {
    Interaction: BackgroundVideo,
});
