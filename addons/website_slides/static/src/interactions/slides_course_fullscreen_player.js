/* global YT, Vimeo */

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import { session } from "@web/session";
import { Quiz } from "@website_slides/interactions/slides_course_quiz";
import { SlideCoursePage } from "@website_slides/interactions/slides_course_page";
import { unhideConditionalElements } from "@website/js/content/inject_dom";
import { SlideShareDialog } from "../js/public/components/slide_share_dialog/slide_share_dialog";
import "@website_slides/interactions/slides_course_join";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { findSlide } from "@website_slides/js/utils";

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
                        this.el.dispatchEvent(new Event("slide_mark_completed"));
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
                this.el.dispatchEvent(new Event("slide_mark_completed"));
            }
        }
    }
}

/**
 * This interaction is responsible of navigation for one slide to another:
 *  - by clicking on any slide list entry
 *  - by mouse click (next / prev)
 *  - by recieving the order to go to prev/next slide (`goPrevious` and `goNext` public methods)
 *
 * The interaction will trigger a `change_slide` event.
 */
export class WebsiteSlidesFullscreenSidebar extends Interaction {
    static selector = ".o_wslides_fs_sidebar";
    dynamicContent = {
        _document: {
            "t-on-keydown": this.onKeyDown,
        },
        ".o_wslides_fs_sidebar_list_item .o_wslides_fs_slide_name": {
            "t-on-click.stop": this.onTabClick,
        },
    };

    setup() {
        this.slidesService = this.services.website_slides;
        this.slides = this.slidesService.data.slides;
        this.slide = this.slidesService.data.slide;
        this.bindedGoNext = this.goNext.bind(this);
        this.slidesService.bus.addEventListener("slide_go_next", this.bindedGoNext);
    }

    destroy() {
        this.slidesService.bus.removeEventListener("slide_go_next", this.bindedGoNext);
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
     * Get the index of the current slide entry (slide and/or quiz)
     */
    getCurrentIndex() {
        const slide = this.slide;
        const currentIndex = this.slides.findIndex(
            (entry) => entry.id === slide.id && entry.isQuiz === slide.isQuiz
        );
        return currentIndex;
    }

    /**
     * Handler called when the user clicks on a normal slide tab
     */
    onTabClick(ev) {
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
     * @param {Object} slide
     */
    updateSlide(slide) {
        if (this.slide === slide) {
            return;
        }
        this.slidesService.setSlide(slide, true);
        this.el.querySelector(".o_wslides_fs_sidebar_list_item.active").classList.remove("active");
        this.el.querySelector(
            `.o_wslides_fs_sidebar_list_item[data-id="${slide.id}"]:not([data-is-quiz="True"])`
        );
        this.el
            .querySelector(
                `.o_wslides_fs_sidebar_list_item[data-id="${slide.id}"]:not([data-is-quiz="True"])`
            )
            .classList.add("active");
        this.el.dispatchEvent(new Event("change_slide"));
    }

    /**
     * Binds left and right arrow to allow the user to navigate between slides
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
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesFullscreenSidebar", WebsiteSlidesFullscreenSidebar);
registry
    .category("public.interactions")
    .add(
        "website_slides.WebsiteSlidesFullscreenYoutubePlayer",
        WebsiteSlidesFullscreenYoutubePlayer
    );
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesFullscreenVimeoPlayer", WebsiteSlidesFullscreenVimeoPlayer);
