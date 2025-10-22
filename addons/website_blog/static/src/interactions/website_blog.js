import { scrollTo } from "@html_builder/utils/scrolling";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { verifyHttpsUrl } from "@website/utils/misc";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class WebsiteBlog extends Interaction {
    static selector = ".website_blog";
    dynamicContent = {
        ".o_wblog_next_button": {
            "t-on-click.prevent": this.onNextBlogClick,
            "t-on-keydown": this.onNextBlogKeydown,
        },
        "#o_wblog_post_content_jump": {
            "t-on-click.prevent.withTarget": this.onContentAnchorClick,
        },
        ".o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete":
            {
                "t-on-click.prevent.withTarget": this.onShareArticleClick,
            },
    };

    /**
     * @param {MouseEvent} ev
     */
    async onNextBlogClick(ev) {
        const blogNextContainerEl = ev.currentTarget.closest("#o_wblog_next_container");
        const nextInfo = blogNextContainerEl.querySelector("#o_wblog_next_post_info").dataset;
        const recordCoverContainerEl = blogNextContainerEl.querySelector(
            ".o_record_cover_container"
        );
        const classes = nextInfo.size.split(" ");
        recordCoverContainerEl.classList.add(...classes, nextInfo.textContent);
        blogNextContainerEl
            .querySelectorAll(".o_wblog_toggle")
            .forEach((el) => el.classList.toggle("d-none"));
        // Appending a placeholder so that the cover can scroll to the top of the
        // screen, regardless of its height.
        const placeholder = document.createElement("div");
        placeholder.style.minHeight = "100vh";
        this.insert(placeholder, this.el.querySelector("#o_wblog_next_container"), "beforeend");
        const nextUrl = verifyHttpsUrl(nextInfo.url);
        await this.forumScrollAction(
            blogNextContainerEl,
            300,
            () => (browser.location.href = nextUrl)
        );
    }
    /**
     * @param {KeyboardEvent} ev
     */
    onNextBlogKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter" || hotkey === "space") {
            return this.onNextBlogClick(ev);
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    async onContentAnchorClick(ev, currentTargetEl) {
        ev.stopImmediatePropagation();
        const scrollTargetEl = document.querySelector(currentTargetEl.hash);

        await this.forumScrollAction(
            scrollTargetEl,
            500,
            () => (browser.location.hash = "blog_content")
        );
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    onShareArticleClick(ev, currentTargetEl) {
        let url = "";
        const blogPostTitle = document.querySelector(".o_wblog_post_name").textContent || "";
        const articleURL = browser.location.href;
        if (currentTargetEl.classList.contains("o_twitter")) {
            const tweetText = _t("Amazing blog article: %(title)s! Check it live: %(url)s", {
                title: blogPostTitle,
                url: articleURL,
            });
            url =
                "https://twitter.com/intent/tweet?tw_p=tweetbutton&text=" +
                encodeURIComponent(tweetText);
        } else if (currentTargetEl.classList.contains("o_facebook")) {
            url = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(articleURL);
        } else if (currentTargetEl.classList.contains("o_linkedin")) {
            url =
                "https://www.linkedin.com/sharing/share-offsite/?url=" +
                encodeURIComponent(articleURL);
        }
        window.open(url, "", "menubar=no, width=500, height=400");
    }

    /**
     * @param {HTMLElement} el - the element we are scrolling to
     * @param {Integer} duration - scroll animation duration
     * @param {Function} callback - to be executed after the scroll is performed
     */
    async forumScrollAction(el, duration, callback) {
        await this.waitFor(scrollTo(el, { duration }));
        callback();
    }
}

registry.category("public.interactions").add("website_blog.website_blog", WebsiteBlog);
