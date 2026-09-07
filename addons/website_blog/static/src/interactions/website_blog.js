import { scrollTo } from "@html_builder/utils/scrolling";
import { StickBelowHeader } from "@website/interactions/sticky_below_header";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { verifyHttpsUrl } from "@website/utils/misc";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { BlogNavSheet } from "./components/blog_nav_sheet";

export class WebsiteBlog extends StickBelowHeader {
    static selector = ".website_blog";
    dynamicContent = {
        ".o_wblog_sheet_trigger": {
            "t-on-click": this.onBlogSheetTriggerClick,
        },
        ".o_wblog_next_button": {
            "t-on-click.prevent": this.onNextBlogClick,
            "t-on-keydown": this.onNextBlogKeydown,
        },
        ...this.dynamicContent,
    };

    setup() {
        super.setup();
        this.stickyEl = this.el.querySelector(".o_sticky_reactive");
        this.defaultPosition = this._isCompactListOrSplitGridView() ? 0 : 16;
        this.position = this.defaultPosition;
    }

    onBlogSheetTriggerClick() {
        const navEl = this.el.querySelector(".o_wblog_category");
        const blogs = [...navEl.querySelectorAll("a")].map((a) => ({
            name: a.textContent.trim(),
            href: a.getAttribute("href"),
            active: a.classList.contains("active"),
        }));
        this.services.bottom_sheet.add(this.el, BlogNavSheet, { blogs });
    }

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
     */
    onShareArticleClick(ev) {
        let url = "";
        const blogPostTitle = document.querySelector(".o_wblog_post_name").textContent || "";
        const articleURL = browser.location.href;
        if (ev.currentTarget.classList.contains("o_twitter")) {
            const tweetText = _t("Amazing blog article: %(title)s! Check it live: %(url)s", {
                title: blogPostTitle,
                url: articleURL,
            });
            url =
                "https://twitter.com/intent/tweet?tw_p=tweetbutton&text=" +
                encodeURIComponent(tweetText);
        } else if (ev.currentTarget.classList.contains("o_facebook")) {
            url = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(articleURL);
        } else if (ev.currentTarget.classList.contains("o_linkedin")) {
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Checks if the layout is "Compact" list view or "Split" grid view (which
     * require zero top default position).
     * (by looking for specific elements that are only present in these views)
     *
     * @private
     * @returns {boolean}
     */
    _isCompactListOrSplitGridView() {
        return (
            this.el.querySelector(".o_wblog_compact_list_month_header") !== null ||
            this.el.querySelector(".o_wblog_split_grid_view_container") !== null
        );
    }
}

registry.category("public.interactions").add("website_blog.website_blog", WebsiteBlog);
