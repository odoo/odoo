/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { scrollTo } from "@web_editor/js/common/scrolling";
import publicWidget from "@web/legacy/js/public/public_widget";
import { share } from "./contentshare";

publicWidget.registry.websiteBlog = publicWidget.Widget.extend({
    selector: '.website_blog',
    events: {
        'click #o_wblog_next_container': '_onNextBlogClick',
        'click #o_wblog_post_content_jump': '_onContentAnchorClick',
        'click .o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete': '_onShareArticle',
    },

    /**
     * @override
     */
    start: function () {
        document.querySelectorAll(".js_tweet, .js_comment").forEach((el) => {
            share(el);
        });

        // Updates the href of an anchor tag when tags list is empty. This will
        // redirect to backend part of the website blog post.
        // TODO: Remove this in the master branch as it will be directly
        // modified in the XML code.
        const blogPostTitleEl = this.el.querySelector("#o_wblog_post_name");
        const emptyTagEl = this.el.querySelector(".o_wblog_sidebar_block #edit-in-backend");
        if (blogPostTitleEl && emptyTagEl) {
            const id = blogPostTitleEl.dataset.blogId;
            emptyTagEl.href = `/odoo/website/blog.post/${id}`;
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onNextBlogClick: function (ev) {
        ev.preventDefault();
        const nexInfo = ev.currentTarget.querySelector("#o_wblog_next_post_info").dataset;
        const recordCoverContainerEl = ev.currentTarget.querySelector(".o_record_cover_container");
        const classes = nexInfo.size.split(" ");
        recordCoverContainerEl.classList.add(...classes, nexInfo.textContent);
        ev.currentTarget.querySelectorAll(".o_wblog_toggle").forEach(el => el.classList.toggle("d-none"));
        // Appending a placeholder so that the cover can scroll to the top of the
        // screen, regardless of its height.
        const placeholder = document.createElement('div');
        placeholder.style.minHeight = '100vh';
        this.el.querySelector("#o_wblog_next_container").append(placeholder);

        // Use setTimeout() to calculate the 'offset()'' only after that size classes
        // have been applyed and that $el has been resized.
        setTimeout(() => {
            this._forumScrollAction(ev.currentTarget, 300, function () {
                window.location.href = nexInfo.url;
            });
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onContentAnchorClick: function (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const currentTargetEl = document.querySelector(ev.currentTarget.hash);

        this._forumScrollAction(currentTargetEl, 500, function () {
            window.location.hash = 'blog_content';
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShareArticle: function (ev) {
        ev.preventDefault();
        let url = "";
        const blogPostTitle = document.querySelector("#o_wblog_post_name").textContent || "";
        const articleURL = window.location.href;
        if (ev.currentTarget.classList.contains("o_twitter")) {
            const tweetText = _t("Amazing blog article: %(title)s! Check it live: %(url)s", {
                title: blogPostTitle,
                url: articleURL,
            });
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=' + encodeURIComponent(tweetText);
        } else if (ev.currentTarget.classList.contains("o_facebook")) {
            url = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(articleURL);
        } else if (ev.currentTarget.classList.contains("o_linkedin")) {
            url = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(articleURL);
        }
        window.open(url, '', 'menubar=no, width=500, height=400');
    },

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {HTMLElement} el - the element we are scrolling to
     * @param {Integer} duration - scroll animation duration
     * @param {Function} callback - to be executed after the scroll is performed
     */
    _forumScrollAction: function (el, duration, callback) {
        scrollTo(el, { duration: duration }).then(() => callback());
    },
});
