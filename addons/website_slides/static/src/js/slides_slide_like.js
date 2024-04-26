/** @odoo-module **/

import { sprintf } from '@web/core/utils/strings';
import { _t } from "@web/core/l10n/translation";
import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from "@web/core/network/rpc";
import '@website_slides/js/slides';

var SlideLikeWidget = publicWidget.Widget.extend({
    events: {
        'click .o_wslides_js_slide_like_up': '_onClickUp',
        'click .o_wslides_js_slide_like_down': '_onClickDown',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} el
     * @param {String} message
     */
    _popoverAlert: function (el, message) {
        new Popover(el, {
            trigger: 'focus',
            delay: {'hide': 300},
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).show();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function (slideId, voteType) {
        const self = this;
        rpc('/slides/slide/like', {
            slide_id: slideId,
            upvote: voteType === 'like',
        }).then(function (data) {
            if (! data.error) {
                const likesBtn = self.el.querySelector('span.o_wslides_js_slide_like_up');
                const likesIcon = likesBtn.querySelector('i.fa');
                const dislikesBtn = self.el.querySelector('span.o_wslides_js_slide_like_down');
                const dislikesIcon = dislikesBtn.querySelector('i.fa');

                // update 'thumbs-up' button with latest state
                likesBtn.dataset.userVote = data.user_vote;
                likesBtn.querySelector('span').textContent = data.likes;
                likesIcon.classList.toggle("fa-thumbs-up", data.user_vote === 1);
                likesIcon.classList.toggle("fa-thumbs-o-up", data.user_vote !== 1);
                // update 'thumbs-down' button with latest state
                dislikesBtn.dataset.userVote = data.user_vote;
                dislikesBtn.querySelector('span').textContent = data.dislikes;
                dislikesIcon.classList.toggle("fa-thumbs-down", data.user_vote === -1);
                dislikesIcon.classList.toggle("fa-thumbs-o-down", data.user_vote !== -1);
            } else {
                if (data.error === 'public_user') {
                    const message = data.error_signup_allowed ?
                        _t('Please <a href="/web/login?redirect=%s">login</a> or <a href="/web/signup?redirect=%s">create an account</a> to vote for this lesson') :
                        _t('Please <a href="/web/login?redirect=%s">login</a> to vote for this lesson');
                    self._popoverAlert(self.el, sprintf(message, encodeURIComponent(document.URL), encodeURIComponent(document.URL)));
                } else if (data.error === 'slide_access') {
                    self._popoverAlert(self.el, _t('You don\'t have access to this lesson'));
                } else if (data.error === 'channel_membership_required') {
                    self._popoverAlert(self.el, _t('You must be member of this course to vote'));
                } else if (data.error === 'channel_comment_disabled') {
                    self._popoverAlert(self.el, _t('Votes and comments are disabled for this course'));
                } else if (data.error === 'channel_karma_required') {
                    self._popoverAlert(self.el, _t('You don\'t have enough karma to vote'));
                } else {
                    self._popoverAlert(self.el, _t('Unknown error'));
                }
            }
        });
    },

    _onClickUp: function (ev) {
        const slideId = ev.currentTarget.dataset.slideId;
        return this._onClick(slideId, 'like');
    },

    _onClickDown: function (ev) {
        const slideId = ev.currentTarget.dataset.slideId;
        return this._onClick(slideId, 'dislike');
    },
});

publicWidget.registry.websiteSlidesSlideLike = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        const self = this;
        const defs = [this._super.apply(this, arguments)];
        this.el.querySelectorAll('.o_wslides_js_slide_like').forEach(function (el) {
            defs.push(new SlideLikeWidget(self).attachTo(el));
        });
        return Promise.all(defs);
    },
});

export default {
    slideLikeWidget: SlideLikeWidget,
    websiteSlidesSlideLike: publicWidget.registry.websiteSlidesSlideLike
};
