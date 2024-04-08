/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";

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
        Array.from(document.querySelectorAll('.js_tweet, .js_comment')).forEach(el => {
            el.share({});
        });
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
        const self = this;
        const el = ev.currentTarget;
        const nexInfo = el.querySelector('#o_wblog_next_post_info').dataset;
        el.querySelector('.o_record_cover_container').classList.add(nexInfo.size, nexInfo.text);
        el.querySelector('.o_wblog_toggle').classList.toggle('d-none');
        // Appending a placeholder so that the cover can scroll to the top of the
        // screen, regardless of its height.
        const placeholder = document.createElement('div');
        placeholder.style.minHeight = '100vh';
        this.el.querySelector('#o_wblog_next_container').append(placeholder);

        // Use setTimeout() to calculate the 'offset()'' only after that size classes
        // have been applyed and that el has been resized.
        setTimeout(() => {
            self._forumScrollAction(el, 300, function () {
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
        const el = document.querySelector(ev.currentTarget.hash);

        this._forumScrollAction(el, 500, function () {
            window.location.hash = 'blog_content';
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShareArticle: function (ev) {
        ev.preventDefault();
        let url = '';
        const element = ev.currentTarget;
        const blogPostTitle = document.querySelector('#o_wblog_post_name').innerHTML || '';
        const articleURL = window.location.href;
        if (element.classList.contains('o_twitter')) {
            const tweetText = _t(
                "Amazing blog article: %s! Check it live: %s",
                blogPostTitle,
                articleURL
            );
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=' + encodeURIComponent(tweetText);
        } else if (element.classList.contains('o_facebook')) {
            url = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(articleURL);
        } else if (element.classList.contains('o_linkedin')) {
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
        dom.scrollTo(el, {duration: duration}).then(() => callback());
    },
});
