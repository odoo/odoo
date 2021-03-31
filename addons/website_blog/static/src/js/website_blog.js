/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteBlog = publicWidget.Widget.extend({
    selector: '.website_blog',
    disabledInEditableMode: false,
    read_events: {
        'click #o_wblog_next_container': '_onNextBlogClick',
        'click #o_wblog_post_content_jump': '_onContentAnchorClick',
        'click .o_twitter, .o_facebook, .o_linkedin, .o_google, .o_twitter_complete, .o_facebook_complete, .o_linkedin_complete, .o_google_complete': '_onShareArticle',
    },

    /**
     * @override
     */
    start() {
        if (!this.editableMode) {
            $('.js_tweet, .js_comment').share({});
        }

        this.widthClasses = ['o_container_small', 'container', 'container-fluid'];

        // The 'o_container_as_first' class is used to mark blocks that need
        // to be kept aligned with the first text block on the blog content.
        // (e.g. breadcrumbs, tags...)
        this.containerSizeUpdatingEls = this.el.querySelectorAll('.o_container_as_first');
        this._adjustWidth();
        for (const el of this.containerSizeUpdatingEls) {
            // Removing the class triggers the fade-in animation.
            el.classList.remove('o_container_as_first');
        }
        // Keep width adjusted upon further updates.
        // TODO Remove event listener once page's core.bus can be reached from editor.
        // core.bus.on('blog_width_update', this, this._adjustWidth);
        this.__boundAdjustWidth = this._adjustWidth.bind(this);
        this.el.addEventListener('blog_width_update', this.__boundAdjustWidth);

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);

        // TODO Remove event listener once page's core.bus can be reached from editor.
        this.el.removeEventListener('blog_width_update', this.__boundAdjustWidth);
        // core.bus.off('blog_width_update', this, this._adjustWidth);

        for (const el of this.containerSizeUpdatingEls) {
            el.classList.remove(...this.widthClasses);
            el.classList.add('o_container_as_first');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adjusts the containers'width class based on the first (text) section of
     * the blog post content.
     * If there is a text section it uses the first text section, otherwise it
     * uses the first section.
     *
     * @private
     */
    _adjustWidth() {
        const blogPostContentEl = this.el.querySelector('.o_wblog_post_content_field');
        if (!blogPostContentEl) {
            return;
        }

        let targetClass = 'o_container_small';
        for (const extraSelector of ['.s_text_block ', ':first-of-type', ':first-of-type ']) {
            const selector = this.widthClasses.map(cls => `section${extraSelector}.${cls}`);
            const source = blogPostContentEl.querySelector(selector);
            if (source) {
                targetClass = this.widthClasses.find(cls => source.classList.contains(cls));
                break;
            }
        }

        for (const containerEl of this.containerSizeUpdatingEls) {
            containerEl.classList.remove(...this.widthClasses);
            containerEl.classList.add(targetClass);
        }
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
        var self = this;
        var $el = $(ev.currentTarget);
        var nexInfo = $el.find('#o_wblog_next_post_info').data();
        $el.find('.o_record_cover_container').addClass(nexInfo.size + ' ' + nexInfo.text).end()
           .find('.o_wblog_toggle').toggleClass('d-none');
        // Appending a placeholder so that the cover can scroll to the top of the
        // screen, regardless of its height.
        const placeholder = document.createElement('div');
        placeholder.style.minHeight = '100vh';
        this.$('#o_wblog_next_container').append(placeholder);

        // Use setTimeout() to calculate the 'offset()'' only after that size classes
        // have been applyed and that $el has been resized.
        setTimeout(() => {
            self._forumScrollAction($el, 300, function () {
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
        var $el = $(ev.currentTarget.hash);

        this._forumScrollAction($el, 500, function () {
            window.location.hash = 'blog_content';
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShareArticle: function (ev) {
        ev.preventDefault();
        var url = '';
        var $element = $(ev.currentTarget);
        var blogPostTitle = $('#o_wblog_post_name').html() || '';
        var articleURL = window.location.href;
        if ($element.hasClass('o_twitter')) {
            var tweetText = _t(
                "Amazing blog article: %s! Check it live: %s",
                blogPostTitle,
                articleURL
            );
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=' + encodeURIComponent(tweetText);
        } else if ($element.hasClass('o_facebook')) {
            url = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(articleURL);
        } else if ($element.hasClass('o_linkedin')) {
            url = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(articleURL);
        }
        window.open(url, '', 'menubar=no, width=500, height=400');
    },

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {JQuery} $el - the element we are scrolling to
     * @param {Integer} duration - scroll animation duration
     * @param {Function} callback - to be executed after the scroll is performed
     */
    _forumScrollAction: function ($el, duration, callback) {
        dom.scrollTo($el[0], {duration: duration}).then(() => callback());
    },
});
