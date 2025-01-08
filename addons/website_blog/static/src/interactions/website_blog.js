import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { scrollTo } from "@web_editor/js/common/scrolling";

export class WebsiteBlog extends Interaction {
    static selector = ".website_blog";
    dynamicContent = {
        "#o_wblog_next_container": {
            "t-on-click.prevent": this.onNextBlogClick,
        },
        "#o_wblog_post_content_jump": {
            "t-on-click.prevent": this.onContentAnchorClick,
        },
        ".o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete": {
            "t-on-click.prevent": this.onShareArticle,
        },
    };

    /**
     * @param {Event} ev
     */
    async onNextBlogClick(ev) {
        const nextInfo = ev.currentTarget.querySelector("#o_wblog_next_post_info").dataset;
        const recordCoverContainerEl = ev.currentTarget.querySelector(".o_record_cover_container");
        const classes = nextInfo.size.split(" ");
        recordCoverContainerEl.classList.add(...classes, nextInfo.textContent);
        ev.currentTarget.querySelectorAll(".o_wblog_toggle").forEach(el => el.classList.toggle("d-none"));
        // Appending a placeholder so that the cover can scroll to the top of the
        // screen, regardless of its height.
        const placeholder = document.createElement("div");
        placeholder.style.minHeight = "100vh";
        this.insert(placeholder, this.el.querySelector("#o_wblog_next_container"), "beforeend");
        await this.forumScrollAction(ev.currentTarget, 300, () => browser.location.href = nextInfo.url);
    }

    /**
     * @param {Event} ev
     */
    async onContentAnchorClick(ev) {
        ev.stopImmediatePropagation();
        const currentTargetEl = document.querySelector(ev.currentTarget.hash);

        await this.forumScrollAction(currentTargetEl, 500, () => browser.location.hash = "blog_content");
    }

    /**
     * @param {Event} ev
     */
    onShareArticle(ev) {
        let url = "";
        const blogPostTitle = document.querySelector("#o_wblog_post_name").textContent || "";
        const articleURL = browser.location.href;
        if (ev.currentTarget.classList.contains("o_twitter")) {
            const tweetText = _t("Amazing blog article: %(title)s! Check it live: %(url)s", {
                title: blogPostTitle,
                url: articleURL,
            });
            url = "https://twitter.com/intent/tweet?tw_p=tweetbutton&text=" + encodeURIComponent(tweetText);
        } else if (ev.currentTarget.classList.contains("o_facebook")) {
            url = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(articleURL);
        } else if (ev.currentTarget.classList.contains("o_linkedin")) {
            url = "https://www.linkedin.com/sharing/share-offsite/?url=" + encodeURIComponent(articleURL);
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

registry
    .category("public.interactions")
    .add("website_blog.website_blog", WebsiteBlog);
