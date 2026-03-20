/* global YT, Vimeo */

import { WebsiteSlidesCommon } from "@website_slides/interactions/slides_course_common";
import "@website_slides/interactions/slides_course_join";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Interaction } from "@web/public/interaction";
import { findSlide, insertHtmlContent } from "@website_slides/js/utils";
import { markup } from "@odoo/owl";
import { unhideConditionalElements } from "@website/utils/misc";
import { TextHighlight } from "@website/interactions/text_highlights";

// The interactions in this file are only used in fullscreen mode

/**
 * This interaction is responsible of display Youtube Player
 *
 * The widget will trigger an event `change_slide` when the video is at
 * its end, and `slide_completed` when the player is at 30 sec before the
 * end of the video (30 sec before is considered as completed).
 */
export class WebsiteSlidesFullscreenYoutubePlayer extends Interaction {
    static selector = ".o_wslides_fs_youtube_player";
    setup() {
        this.youtubeUrl = "https://www.youtube.com/iframe_api";
        this.slidesService = this.services.website_slides;
        this.slide = this.slidesService.data.slide;
        this.channel = this.slidesService.data.channel;
        this.player = null;
        this.tid = null;
    }

    async willStart() {
        await this.loadYoutubeAPI();
    }

    start() {
        this.setupYoutubePlayer();
    }

    destroy() {
        if (this.tid) {
            clearInterval(this.tid);
        }
    }

    loadYoutubeAPI() {
        return new Promise((resolve) => {
            if (!document.querySelector(`script[src="${this.youtubeUrl}"]`)) {
                const youtubeEl = document.createElement("script");
                youtubeEl.src = this.youtubeUrl;
                this.insert(youtubeEl, document.body, "beforeend");

                // function called when the Youtube asset is loaded
                // see https://developers.google.com/youtube/iframe_api_reference#Requirements
                window.onYouTubeIframeAPIReady = () => {
                    resolve();
                };
            } else {
                resolve();
            }
        });
    }

    /**
     * Links the youtube api to the iframe present in the template
     */
    setupYoutubePlayer() {
        this.player = new YT.Player(`youtube-player${this.slide.id}`, {
            playerVars: {
                autoplay: 1,
                origin: window.location.origin,
            },
            events: {
                onStateChange: this.onPlayerStateChange.bind(this),
            },
        });
    }
    /**
     * Specific method of the youtube api.
     * Whenever the player starts playing/pausing/buffering/..., a setinterval is created.
     * This setinterval is used to check te user's progress in the video.
     * Once the user reaches a particular time in the video (30s before end), the slide will be considered as completed
     * if the video doesn't have a mini-quiz.
     * This method also allows to automatically go to the next slide (or the quiz associated to the current
     * video) once the video is over
     * @param {*} event
     */
    onPlayerStateChange(event) {
        if (this.isDestroyed) {
            return;
        }
        if (event.data !== YT.PlayerState.ENDED) {
            if (!event.target.getCurrentTime) {
                return;
            }

            if (this.tid) {
                clearInterval(this.tid);
            }

            let currentVideoTime = event.target.getCurrentTime();
            const totalVideoTime = event.target.getDuration();
            this.tid = setInterval(() => {
                currentVideoTime += 1;
                if (totalVideoTime && currentVideoTime > totalVideoTime - 30) {
                    if (this.channel.isMember && !this.slide.hasQuestion && !this.slide.completed) {
                        this.el.dispatchEvent(new Event("slide_set_completed"));
                    }
                }
            }, 1000);
        } else {
            if (this.tid) {
                clearInterval(this.tid);
            }
            this.player = null;
            if (this.slide.hasNext) {
                this.slidesService.bus.trigger("slide_go_next");
            }
        }
    }
}

/**
 * This interaction is responsible of loading the Vimeo video.
 *
 * Similarly to the YouTube implementation, the widget will trigger an event `change_slide` when
 * the video is at its end, and `slide_completed` when the player is at 30 sec before the end of
 * the video (30 sec before is considered as completed).
 *
 * See https://developer.vimeo.com/player/sdk/reference for all the API documentation.
 */
export class WebsiteSlidesFullscreenVimeoPlayer extends Interaction {
    static selector = ".o_wslides_fs_vimeo_player";
    setup() {
        this.vimeoUrl = "https://player.vimeo.com/api/player.js";
        this.slidesService = this.services.website_slides;
        this.slide = this.slidesService.data.slide;
        this.channel = this.slidesService.data.channel;
        this.player = null;
        this.videoDuration = 0;
    }

    async willStart() {
        await this.loadVimeoAPI();
    }

    start() {
        this.setupVimeoPlayer();
    }

    loadVimeoAPI() {
        return new Promise((resolve) => {
            if (!document.querySelector(`script[src="${this.vimeoUrl}"]`)) {
                const vimeoEl = document.createElement("script");
                vimeoEl.src = this.vimeoUrl;
                this.insert(vimeoEl, document.body, "beforeend");
                vimeoEl.onload = () => {
                    resolve();
                };
            } else {
                resolve();
            }
        });
    }

    /**
     * Instantiate the Vimeo player and register the various events.
     */
    async setupVimeoPlayer() {
        this.player = new Vimeo.Player(this.el.querySelector("iframe"));
        this.videoDuration = await this.waitFor(this.player.getDuration());
        this.player.on("timeupdate", this.onVideoTimeUpdate.bind(this));
        this.player.on("ended", this.onVideoEnded.bind(this));
    }

    /**
     * When the player triggers the 'ended' event, we go to the next slide if there is one.
     * See https://developer.vimeo.com/player/sdk/reference#ended for more information
     */
    onVideoEnded() {
        if (this.slide.hasNext) {
            this.slidesService.bus.trigger("slide_go_next");
        }
    }

    /**
     * Every time the video changes position, both while viewing and also when seeking manually,
     * Vimeo triggers this handy 'timeupdate' event.
     * We use it to set the slide as completed as soon as we reach the end (30 last seconds).
     *
     * See https://developer.vimeo.com/player/sdk/reference#timeupdate for more information
     *
     * @param {Object} eventData the 'timeupdate' event data
     */
    async onVideoTimeUpdate(eventData) {
        if (eventData.seconds > this.videoDuration - 30) {
            if (this.channel.isMember && !this.slide.hasQuestion && !this.slide.completed) {
                this.el.dispatchEvent(new Event("slide_set_completed"));
            }
        }
    }
}

export class FullscreenTextHighlight extends TextHighlight {
    static selector = ".o_wslide_fs_article_content";
}

/**
 * This interaction is responsible of navigation for one slide to another:
 *  - by clicking on any slide list entry
 *  - by mouse click (next / prev)
 *  - by recieving the order to go to prev/next slide (`goPrevious` and `goNext` public methods)
 *
 * The interaction will trigger a `change_slide` event.
 */
export class WebsiteSlidesFullscreen extends WebsiteSlidesCommon {
    static selector = ".o_wslides_fs_main";
    dynamicContent = {
        ...this.dynamicContent,
        _document: {
            "t-on-keydown": this.onKeyDown,
        },
        ".o_footer": {
            "t-att-class": () => ({ "d-none": true }),
        },
        ".o_wslides_fs_content": {
            "t-att-class": () => ({
                "bg-white": this.slide.category === "quiz" || this.slide.isQuiz,
            }),
        },
        ".o_wslides_fs_sidebar_list_item .o_wslides_fs_slide_name": {
            "t-on-click.stop": this.onSidebarItemClick,
        },
        ".o_wslides_fs_sidebar": {
            "t-att-class": () => ({ o_wslides_fs_sidebar_hidden: this.sidebarHidden }),
        },
        ".o_wslides_fs_toggle_sidebar": {
            "t-att-class": () => ({ active: !this.sidebarHidden }),
            "t-on-click.prevent": this.toggleSidebar,
        },
        ".o_wslides_fs_youtube_player, .o_wslides_fs_vimeo_player": {
            "t-on-slide_set_completed": this.onSlideSetCompleted,
        },
    };

    setup() {
        super.setup();
        this.dialog = this.services.dialog;

        this.data = this.slidesService.data;
        this.slides = this.data.slides;

        this.sidebarHidden = false;
        this.renderSlideRunning = false;
        const slideId = this.getCurrentSlideId();

        this.slidesService.setSlides(this.preprocessSlideData(this.getSlides()));
        this.slidesService.setChannel(this.extractChannelData());
        const urlParams = new URL(window.location).searchParams;
        if (slideId) {
            this.slidesService.setSlide(
                findSlide(this.slides, {
                    id: slideId,
                    isQuiz: String(urlParams.get("quiz")) === "1",
                })
            );
        } else {
            this.slidesService.setSlide(this.slides[0]);
        }
        this.bindedGoNext = this.goNext.bind(this);
        this.slidesService.bus.addEventListener("slide_go_next", this.bindedGoNext);
        document.querySelector(".o_frontend_to_backend_nav")?.remove();
        this.changeSlide();
    }

    destroy() {
        this.slidesService.bus.removeEventListener("slide_go_next", this.bindedGoNext);
    }

    /**
     * Binds left and right arrow to allow the user to navigate between slides.
     */
    onKeyDown(ev) {
        switch (ev.key) {
            case "ArrowLeft":
                this.goPrevious();
                break;
            case "ArrowRight":
                this.goNext();
                break;
        }
    }

    /**
     * Change the current slide with the next one (if there is one).
     */
    goNext() {
        const currentIndex = this.getCurrentIndex();
        if (currentIndex < this.slides.length - 1) {
            this.updateSlide(this.slides[currentIndex + 1]);
        }
    }

    /**
     * Change the current slide with the previous one (if there is one).
     */
    goPrevious() {
        const currentIndex = this.getCurrentIndex();
        if (currentIndex >= 1) {
            this.updateSlide(this.slides[currentIndex - 1]);
        }
    }

    /**
     * Get the index of the current slide entry (slide and/or quiz).
     */
    getCurrentIndex() {
        return this.slides.findIndex(
            (entry) => entry.id === this.slide.id && entry.isQuiz === this.slide.isQuiz
        );
    }

    /**
     * Handler called when the user clicks on a normal slide tab
     */
    onSidebarItemClick(ev) {
        const el = ev.currentTarget.closest(".o_wslides_fs_sidebar_list_item");
        const data = el.dataset;
        if (data.canAccess) {
            const isQuiz = !!data.isQuiz;
            const slideId = Number(data.id);
            const slide = findSlide(this.slides, { id: slideId, isQuiz });
            this.updateSlide(slide);
        }
    }

    /**
     * Actively changes the active tab in the sidebar so that it corresponds
     * the slide currently displayed
     *
     * @param {Object} slide
     */
    updateSlide(slide) {
        if (this.slide === slide) {
            return;
        }
        this.slidesService.setSlide(slide, true);
        this.el.querySelector(".o_wslides_fs_sidebar_list_item.active").classList.remove("active");
        this.el
            .querySelector(
                `.o_wslides_fs_sidebar_list_item[data-id="${slide.id}"]:not([data-is-quiz="True"])`
            )
            .classList.add("active");
        this.changeSlide();
    }

    /**
     * Fetches content with an rpc call for slides of category "article"
     */
    async fetchHtmlContent() {
        if (this.slide.htmlContentFetched) {
            return;
        }
        const data = await this.waitFor(
            rpc("/slides/slide/get_html_content", {
                slide_id: this.slide.id,
            })
        );
        if (data.html_content) {
            this.slide.htmlContent = data.html_content;
        } else {
            this.slide.htmlContent = "";
        }
        this.slide.htmlContentFetched = true;
    }

    /**
     * Fetches slide content depending on its category.
     * If the slide doesn't need to fetch any content, return a resolved deferred
     */
    fetchSlideContent() {
        if (this.slide.category === "article" && !this.slide.isQuiz) {
            return this.fetchHtmlContent();
        }
        return Promise.resolve();
    }

    stringToElements(str) {
        return new DOMParser().parseFromString(str, "text/html").body.children;
    }

    /**
     * Extend the slide data list to add information about rendering method, and other
     * specific values according to their slide_category.
     */
    preprocessSlideData(slidesDataList) {
        for (const [index, slideData] of slidesDataList.entries()) {
            slideData.hasNext = index < slidesDataList.length - 1;
            // compute embed url
            if (slideData.category === "video" && slideData.videoSourceType !== "vimeo") {
                // embedCode contains an iframe tag, where src attribute is the url (youtube or embed document from odoo)
                slideData.embedCode = this.stringToElements(slideData.embedCode)[0]?.src || "";
                const scheme = slideData.embedCode.indexOf("//") === 0 ? "https:" : "";
                if (slideData.embedCode) {
                    const url = new URL(scheme + slideData.embedCode);
                    const params = url.searchParams;
                    params.set("rel", 0);
                    params.set("enablejsapi", 1);
                    params.set("origin", window.location.origin);
                    if (slideData.embedCode.indexOf("//drive.google.com") === -1) {
                        params.set("autoplay", 1);
                    }
                    slideData.embedUrl = url.href;
                } else {
                    slideData.embedUrl = "";
                }
            } else if (slideData.category === "infographic") {
                slideData.embedUrl = `/web/image/slide.slide/${encodeURIComponent(
                    slideData.id
                )}/image_1024`;
            } else if (slideData.category === "document") {
                slideData.embedUrl = this.stringToElements(slideData.embedCode)[0]?.src;
            }
            // fill empty property to allow searching on it with list.filter(matcher)
            slideData.isQuiz = !!slideData.isQuiz;
            slideData.hasQuestion = !!slideData.hasQuestion;
            // technical settings for the Fullscreen to work
            let autoSetDone = false;
            if (!slideData.hasQuestion) {
                // images, documents (local + external) and articles are marked as completed when opened
                // google drive videos do not benefit from the YouTube integration and are marked as completed when opened
                if (
                    ["infographic", "document", "article"].includes(slideData.category) ||
                    (slideData.category === "video" && slideData.videoSourceType === "google_drive")
                ) {
                    autoSetDone = true;
                }
            }
            slideData.autoSetDone = autoSetDone;
        }
        return slidesDataList;
    }

    /**
     * Changes the url whenever the user changes slides.
     * This allows the user to refresh the page and stay on the right slide
     */
    pushUrlState() {
        const urlParts = window.location.pathname.split("/");
        urlParts[urlParts.length - 1] = this.slide.slug;
        const url = urlParts.join("/");
        this.el.querySelector(".o_wslides_fs_exit_fullscreen").href = url;
        const fullscreenUrl = new URL(url, window.location.origin);
        const params = fullscreenUrl.searchParams;
        params.set("fullscreen", 1);
        if (this.slide.isQuiz) {
            params.set("quiz", 1);
        }
        history.pushState(null, "", fullscreenUrl.href);
    }

    /**
     * Render the current slide content using specific mechanism according to slide category:
     * - simply append content (for article)
     * - template rendering (for image, document, ....)
     * @returns {Boolean} true if rendered
     */
    renderSlide() {
        // Avoid concurrent execution of the slide rendering as it writes the content at the same place anyway.
        if (this.renderSlideRunning) {
            return false;
        }
        this.renderSlideRunning = true;
        try {
            const slide = this.slide;
            const contentEl = this.el.querySelector(".o_wslides_fs_content");
            contentEl.replaceChildren();

            // display quiz slide, or quiz attached to a slide
            if (slide.category === "quiz" || slide.isQuiz) {
                this.renderAt("slide.slide.quiz", this.data, contentEl);
            } else if (["document", "infographic"].includes(slide.category)) {
                this.renderAt("website.slides.fullscreen.content", this.data, contentEl);
            } else if (slide.category === "video") {
                this.renderAt(
                    `website.slides.fullscreen.video.${slide.videoSourceType}`,
                    this.data,
                    contentEl
                );
            } else if (slide.category === "article") {
                const containerEl = document.createElement("div");
                containerEl.classList.add(
                    "o_wslide_fs_article_content",
                    "bg-white",
                    "block",
                    "w-100",
                    "overflow-auto",
                    "p-3"
                );
                insertHtmlContent(this, slide.htmlContent, containerEl, "beforeend");
                this.insert(containerEl, contentEl);
            }
            unhideConditionalElements();
        } finally {
            this.renderSlideRunning = false;
        }
        return true;
    }
    //TODO: I would rename this as updateSlide and obviously change the updateSlide to something else...
    async changeSlide() {
        this.pushUrlState();
        await this.waitFor(this.fetchSlideContent());
        await this.waitFor(this.slidesService.fetchQuiz());

        // render content
        const websiteName = document.title.split(" | ").at(-1); // get the website name from title
        document.title = websiteName ? this.slide.name + " | " + websiteName : this.slide.name;
        if (uiUtils.getSize() < SIZES.MD) {
            this.toggleSidebar(); // hide sidebar when small device screen
        }
        this.renderSlide();
        if (this.slide.autoSetDone && !session.is_public) {
            // no useless RPC call
            if (this.slide.category === "document") {
                // only set the slide as completed after iFrame is loaded to avoid concurrent execution with 'embedUrl' controller
                this.addListener(
                    this.el.querySelector("iframe.o_wslides_iframe_viewer"),
                    "load",
                    () => this.slidesService.toggleCompletion(this.slide),
                    { once: true }
                );
            } else {
                this.slidesService.toggleCompletion(this.slide);
            }
        }
    }

    onSlideSetCompleted() {
        if (!session.is_public) {
            this.slidesService.toggleCompletion(this.slide);
        }
    }

    /**
     * After a slide has been marked as completed / uncompleted, update the state
     * of this slide and reload the slide if needed (e.g. to re-show the questions
     * of a quiz).
     *
     * @param {Object} slide: slide to set as completed
     */
    async onSlideCompleted(slide = this.slide) {
        super.onSlideCompleted(slide);
        if (this.slide.id === slide.id && this.slide.hasQuestion && !slide.completed) {
            this.renderSlide();
        }
    }

    /**
     * Toggles sidebar visibility.
     */
    toggleSidebar() {
        this.sidebarHidden = !this.sidebarHidden;
    }

    extractChannelData() {
        return {
            id: Number(this.el.dataset.channelId),
            enroll: this.el.dataset.channelEnroll,
        };
    }

    getCurrentSlideId() {
        return parseInt(this.el.querySelector(".o_wslides_fs_sidebar_list_item.active").dataset.id);
    }

    /**
     * To override in other modules to get more slides data
     * e.g. in website_slides_survey
     */
    getAdditionalSlidesData(data) {
        return {};
    }

    /**
     * Creates slides objects from every slide-list-cells attributes
     */
    getSlides() {
        const slideList = [];
        let channelSet = false;
        for (const slideEl of this.el.querySelectorAll(
            ".o_wslides_fs_sidebar_list_item[data-can-access='True']"
        )) {
            const data = slideEl.dataset;
            slideList.push({
                id: Number(data.id),
                canAccess: !!data.canAccess,
                name: data.name,
                category: data.category,
                videoSourceType: data.videoSourceType,
                slug: data.slug,
                hasQuestion: !!data.hasQuestion,
                isQuiz: !!data.isQuiz,
                completed: !!data.completed,
                embedCode: data.embedCode && markup(data.embedCode),
                canSelfMarkCompleted: !!data.canSelfMarkCompleted,
                canSelfMarkUncompleted: !!data.canSelfMarkUncompleted,
                emailSharing: !!data.emailSharing,
                websiteShareUrl: data.websiteShareUrl,
                ...this.getAdditionalSlidesData(data),
            });

            if (!channelSet) {
                this.slidesService.setChannel({
                    isMember: !!data.isMember,
                    isMemberOrInvited: !!data.isMemberOrInvited,
                    canUpload: !!data.canUpload,
                });
                channelSet = true;
            }
        }
        return slideList;
    }
}

registry.category("public.interactions").add("website_slides.text_highlight", FullscreenTextHighlight);
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesFullscreen", WebsiteSlidesFullscreen);
registry
    .category("public.interactions")
    .add(
        "website_slides.WebsiteSlidesFullscreenYoutubePlayer",
        WebsiteSlidesFullscreenYoutubePlayer
    );
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesFullscreenVimeoPlayer", WebsiteSlidesFullscreenVimeoPlayer);
