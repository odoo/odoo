import { Interaction } from "@web/public/interaction";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { findSlide, insertHtmlContent } from "@website_slides/js/utils";
import { markup } from "@odoo/owl";
import { unhideConditionalElements } from "@website/utils/misc";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { SlideShareDialog } from "@website_slides/js/public/components/slide_share_dialog/slide_share_dialog";
import { redirect } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

export class WebsiteSlidesCoursePage extends Interaction {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _progressPercentage: () =>
            document.querySelector(
                ".o_wslides_channel_completion_progressbar .o_wslides_progress_percentage"
            ),
        _progressBar: () =>
            document.querySelector(".o_wslides_channel_completion_progressbar .progress-bar"),
    };
    dynamicContent = {
        "button.o_wslides_button_complete": {
            "t-on-click.prevent": this.onCompleteClick,
        },
        ".o_wslides_channel_completion_progressbar": {
            "t-att-class": () => ({
                "d-none": this.progressbarCompletion >= 100,
                "d-flex": this.progressbarCompletion < 100,
            }),
        },
        ".o_wslides_channel_completion_completed": {
            "t-att-class": () => ({ "d-none": this.progressbarCompletion < 100 }),
        },
        _progressBar: {
            "t-att-style": () => ({ width: `${this.progressbarCompletion}%` }),
        },
        _progressPercentage: {
            "t-out": () => this.progressbarCompletion,
        },
        _root: {
            "t-on-slide_completed": this.onSlideCompleted,
        },
        ".o_wslides_fs_youtube_player, .o_wslides_fs_vimeo_player": {
            "t-on-slide_mark_completed": this.onSlideMarkCompleted,
        },
    };

    setup() {
        this.slidesService = this.services.website_slides;
        this.user = this.slidesService.data.user;
        this.slide = this.slidesService.data.slide;
        this.channel = this.slidesService.data.channel;
        this.progressbarCompletion = parseInt(
            document.querySelector(
                ".o_wslides_channel_completion_progressbar .o_wslides_progress_percentage"
            )?.textContent || 0
        );
    }

    /**
     * Collapse the next category when the current one has just been completed
     */
    collapseNextCategory(nextCategoryId) {
        const categorySectionEl = document.querySelector(`#category-collapse-${nextCategoryId}`);
        if (categorySectionEl?.getAttribute("aria-expanded") === "false") {
            categorySectionEl.setAttribute("aria-expanded", true);
            document.querySelector(`ul[id=collapse-${nextCategoryId}]`).classList.add("show");
        }
    }

    /**
     * Greens up the bullet when the slide is completed
     * @param {Object} slide
     * @param {Boolean} completed
     */
    toggleCompletionButton(slide, completed = true) {
        const buttonEl = this.el.querySelector(
            `.o_wslides_sidebar_done_button[data-id="${slide.id}"]`
        );
        if (!buttonEl) {
            return;
        }
        const newButtonEl = renderToElement("website.slides.sidebar.done.button", {
            slideId: slide.id,
            uncompletedIcon: buttonEl.dataset.uncompletedIcon ?? "fa-circle-thin",
            slideCompleted: completed ? 1 : 0,
            canSelfMarkUncompleted: slide.canSelfMarkUncompleted,
            canSelfMarkCompleted: slide.canSelfMarkCompleted,
            isMember: this.channel.isMember,
        });
        buttonEl.replaceWith(newButtonEl);
    }

    /**
     * Updates the progressbar whenever a lesson is completed
     * @param {Integer} channelCompletion
     */
    updateProgressbar(channelCompletion) {
        this.progressbarCompletion = Math.min(100, channelCompletion);
        this.updateContent();
    }

    /**
     * Once the completion conditions are filled,
     * rpc call to set the relation between the slide and the user as "completed"
     * @param {Object} slide: slide to set as completed
     * @param {Boolean} completed: true to mark the slide as completed
     *     false to mark the slide as not completed
     */
    async toggleSlideCompleted(slide, completed = true) {
        if (
            !!slide.completed === !!completed ||
            !this.channel.isMember ||
            (completed && !slide.canSelfMarkCompleted) ||
            (!completed && !slide.canSelfMarkUncompleted)
        ) {
            // no useless RPC call
            return false;
        }
        const data = await this.waitFor(
            rpc(`/slides/slide/${completed ? "set_completed" : "set_uncompleted"}`, {
                slide_id: slide.id,
            })
        );

        this.toggleCompletionButton(slide, completed);
        this.updateProgressbar(data.channel_completion);
        if (data.next_category_id) {
            this.collapseNextCategory(data.next_category_id);
        }
        if (this.slide.id === slide.id) {
            this.slide.completed = completed;
        }

        return true;
    }

    /**
     * We clicked on the "done" button.
     * It will make a RPC call to update the slide state and update the UI.
     * @param {Event} event
     */
    onCompleteClick(event) {
        event.stopPropagation();
        const data = event.currentTarget.closest(".o_wslides_sidebar_done_button").dataset;
        const slide = {
            id: Number(data.id),
            uncompletedIcon: data.uncompletedIcon,
            completed: !!data.completed,
            canSelfMarkCompleted: !!data.canSelfMarkCompleted,
            canSelfMarkUncompleted: !!data.canSelfMarkUncompleted,
        };
        this.channel.isMember = !!data.isMember;
        if (data.id === this.slide.id) {
            this.slidesService.setSlide(slide);
        }
        this.toggleSlideCompleted(slide, !slide.completed);
    }

    /**
     * The slide has been completed, update the UI
     * @param {Event} event
     */
    onSlideCompleted(event) {
        this.toggleCompletionButton(this.slide, this.slide.completed);
        this.updateProgressbar(event.detail.channelCompletion);
    }

    /**
     * Make a RPC call to complete the slide then update the UI
     */
    onSlideMarkCompleted() {
        if (!this.user.public) {
            this.toggleSlideCompleted(this.slide, true);
        }
    }
}

export class WebsiteSlidesCoursePageFullscreen extends WebsiteSlidesCoursePage {
    static selector = ".o_wslides_fs_main";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _footer: () => document.querySelector(".o_footer"),
    };
    dynamicContent = {
        ...this.dynamicContent,
        _footer: {
            "t-att-class": () => ({ "d-none": !this.showFooter }),
        },
        ".o_wslides_fs_content": {
            "t-att-class": () => ({
                "bg-white": this.slide.category === "quiz" || this.slide.isQuiz,
            }),
        },
        ".o_wslides_fs_sidebar": {
            "t-on-change_slide": this.onSlideChange,
            "t-att-class": () => ({ o_wslides_fs_sidebar_hidden: this.sidebarHidden }),
        },
        ".o_wslides_fs_toggle_sidebar": {
            "t-att-class": () => ({ active: !this.sidebarHidden }),
            "t-on-click.prevent": this.onToggleSidebarClick,
        },
        ".o_wslides_fs_share": {
            "t-on-click": this.onShareSlideClick,
        },
    };

    setup() {
        super.setup();
        this.dialog = this.services.dialog;
        this.slidesService = this.services.website_slides;
        this.data = this.slidesService.data;
        this.slides = this.data.slides;
        this.quiz = this.data.quiz;

        // To prevent double scrollbar due to footer overflow
        this.showFooter = false;
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
        document.querySelector(".o_frontend_to_backend_nav")?.remove();
        this.onSlideChange();
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

    getDocumentMaxPage() {
        const iframe = this.el.querySelector("iframe.o_wslides_iframe_viewer");
        const iframeDocument = iframe.contentWindow.document;
        return parseInt(iframeDocument.querySelector("#page_count").innerText);
    }

    stringToElements(str) {
        return new DOMParser().parseFromString(str, "text/html").body.children;
    }

    /**
     * Extend the slide data list to add informations about rendering method, and other
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
            } else if (slideData.category === "video" && slideData.videoSourceType === "vimeo") {
                slideData.embedCode = markup(slideData.embedCode);
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
                if (["infographic", "document", "article"].includes(slideData.category)) {
                    autoSetDone = true; // images, documents (local + external) and articles are marked as completed when opened
                } else if (
                    slideData.category === "video" &&
                    slideData.videoSourceType === "google_drive"
                ) {
                    autoSetDone = true; // google drive videos do not benefit from the YouTube integration and are marked as completed when opened
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
     * Render the current slide content using specific mecanism according to slide category:
     * - simply append content (for article)
     * - template rendering (for image, document, ....)
     */
    async renderSlide() {
        // Avoid concurrent execution of the slide rendering as it writes the content at the same place anyway.
        if (this.renderSlideRunning) {
            return;
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
                contentEl.replaceChildren();
                this.renderAt("website.slides.fullscreen.content", this, contentEl);
            } else if (slide.category === "video" && slide.videoSourceType === "youtube") {
                this.renderAt("website.slides.fullscreen.video.youtube", this, contentEl);
            } else if (slide.category === "video" && slide.videoSourceType === "vimeo") {
                this.renderAt("website.slides.fullscreen.video.vimeo", this, contentEl);
            } else if (slide.category === "video" && slide.videoSourceType === "google_drive") {
                contentEl.replaceChildren();
                this.renderAt("website.slides.fullscreen.video.google_drive", this, contentEl);
            } else if (slide.category === "article") {
                const containerEl = document.createElement("div");
                for (const className of [
                    "o_wslide_fs_article_content",
                    "bg-white",
                    "block",
                    "w-100",
                    "overflow-auto",
                    "p-3",
                ]) {
                    containerEl.classList.add(className);
                }
                insertHtmlContent(this, slide.htmlContent, containerEl, "beforeend");
                this.insert(containerEl, contentEl);
            }
            unhideConditionalElements();
        } finally {
            this.renderSlideRunning = false;
        }
    }

    async onSlideChange() {
        const slide = this.slide;
        this.pushUrlState();
        await this.waitFor(this.fetchSlideContent());
        await this.waitFor(this.slidesService.fetchQuiz());

        // render content
        const websiteName = document.title.split(" | ")[1]; // get the website name from title
        document.title = websiteName ? slide.name + " | " + websiteName : slide.name;
        if (uiUtils.getSize() < SIZES.MD) {
            this.toggleSidebar(); // hide sidebar when small device screen
        }
        await this.waitFor(this.renderSlide());
        if (slide.autoSetDone && !this.user.public) {
            // no useless RPC call
            if (slide.category === "document") {
                // only set the slide as completed after iFrame is loaded to avoid concurrent execution with 'embedUrl' controller
                this.addListener(
                    this.el.querySelector("iframe.o_wslides_iframe_viewer"),
                    "load",
                    () => this.toggleSlideCompleted(slide),
                    { once: true }
                );
            } else {
                return this.toggleSlideCompleted(slide);
            }
        }
    }

    /**
     * After a slide has been marked as completed / uncompleted, update the state
     * of this slide and reload the slide if needed (e.g. to re-show the questions
     * of a quiz).
     *
     * We might need to set multiple slide as completed, because of "isQuiz"
     * set to True / False
     * @param {Object} slide: slide to set as completed
     * @param {Boolean} completed: true to mark the slide as completed
     *     false to mark the slide as not completed
     */
    async toggleSlideCompleted(slide, completed = true) {
        if (!(await this.waitFor(super.toggleSlideCompleted(...arguments)))) {
            return;
        }
        const fsSlides = this.slides.filter((_slide) => _slide.id === slide.id);
        for (const slide of fsSlides) {
            slide.completed = completed;
        }

        if (this.slide.id === slide.id) {
            this.slide.completed = completed;
            if ((this.slide.hasQuestion || this.slide.category === "quiz") && !completed) {
                // Reload the quiz
                this.renderSlide();
            }
        }
    }

    /**
     * Called when the sidebar toggle is clicked -> toggles the sidebar visibility.
     */
    onToggleSidebarClick() {
        this.toggleSidebar();
    }

    onShareSlideClick() {
        const slide = this.slide;
        this.dialog.add(SlideShareDialog, {
            category: slide.category,
            documentMaxPage: slide.category == "document" && this.getDocumentMaxPage(),
            emailSharing: slide.emailSharing,
            embedCode: slide.embedCode || "",
            id: slide.id,
            isFullscreen: true,
            name: slide.name,
            url: slide.websiteShareUrl,
        });
    }

    /**
     * Toggles sidebar visibility.
     */
    toggleSidebar() {
        this.sidebarHidden = !this.sidebarHidden;
    }

    extractChannelData() {
        const data = this.el.data;
        return {
            id: Number(data.channelId),
            enroll: data.channelEnroll,
        };
    }

    getCurrentSlideId() {
        return parseInt(this.el.querySelector(".o_wslides_fs_sidebar_list_item.active").dataset.id);
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
                embedCode: data.embedCode,
                canSelfMarkCompleted: !!data.canSelfMarkCompleted,
                canSelfMarkUncompleted: !!data.canSelfMarkUncompleted,
                emailSharing: !!data.emailSharing,
                websiteShareUrl: data.websiteShareUrl,
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

class WebsiteSlidesCoursePageNoFullscreen extends WebsiteSlidesCoursePage {
    static selector = ".o_wslides_lesson_main";
    dynamicContent = {
        ...this.dynamicContent,
    };

    setup() {
        super.setup();
        this.slidesService = this.services.website_slides;
        this.quiz = this.slidesService.data.quiz;
        this.bindedOnQuizNextSlide = this.onQuizNextSlide.bind(this);
        this.slidesService.bus.addEventListener("slide_go_next", this.bindedOnQuizNextSlide);
    }

    destroy() {
        this.slidesService.bus.removeEventListener("slide_go_next", this.bindedOnQuizNextSlide);
    }

    async willStart() {
        // this.slide and this.quiz must be set by WebsiteSlidesQuizNoFullscreen
        await this.slidesService.ready.slide;
        await this.slidesService.ready.quiz;
    }

    onQuizNextSlide() {
        const url = this.el.querySelector(".o_wslides_js_lesson_quiz").dataset.nextSlideUrl;
        redirect(url);
    }

    /**
     * After a slide has been marked as completed / uncompleted, update the state
     * of this interaction and reload the slide if needed (e.g. to re-show the questions
     * of a quiz).
     * @override
     * @param {Object} slide
     * @param {Boolean} completed
     */
    async toggleCompletionButton(slide, completed = true) {
        super.toggleCompletionButton(...arguments);
        if (
            this.slide.hasQuestion &&
            this.slide.id === slide.id &&
            !completed &&
            this.quiz.questionCount
        ) {
            // The quiz has been marked as "Not Done", re-load the questions

            // Option 1: Reload the page
            // window.location.reload();

            // Option 2: Update the quiz dynamically using the fullscreen quiz template
            this.slidesService.setQuiz({
                answers: [],
                sessionAnswers: [],
            });
            this.slide.completed = false;
            await this.slidesService.fetchQuiz(true);
            const previousQuizEl = this.el.querySelector(
                ".o_wslides_js_quiz_container, .o_wslides_fs_quiz_container"
            );
            this.renderAt("slide.slide.quiz", this.slidesService.data, previousQuizEl, "afterend");
            previousQuizEl.remove();
        }

        // The quiz has been submitted in a documentation and in non fullscreen view,
        // should update the button "Mark Done" to "Mark To Do"
        const doneButtonEl = this.el.querySelector(".o_wslides_done_button");
        if (doneButtonEl && completed) {
            doneButtonEl.classList.remove(
                "o_wslides_done_button",
                "disabled",
                "btn-primary",
                "text-white"
            );
            doneButtonEl.classList.add("o_wslides_undone_button", "btn-light");
            doneButtonEl.removeAttribute("title");
            doneButtonEl.removeAttribute("aria-disabled");
            doneButtonEl.href = `/slides/slide/${encodeURIComponent(slide.id)}/set_uncompleted`;
            doneButtonEl.textContent = _t("Mark To Do");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesFullscreenPlayer", WebsiteSlidesCoursePageFullscreen);
registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesCoursePageQuiz", WebsiteSlidesCoursePageNoFullscreen);
