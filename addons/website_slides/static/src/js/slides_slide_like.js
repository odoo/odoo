/** @odoo-module **/

import { sprintf } from '@web/core/utils/strings';
import { _t } from 'web.core';
import publicWidget from 'web.public.widget';
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
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            delay: {'hide': 300},
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function (slideId, voteType) {
        var self = this;
        this._rpc({
            route: '/slides/slide/like',
            params: {
                slide_id: slideId,
                upvote: voteType === 'like',
            },
        }).then(function (data) {
            if (! data.error) {
                const $likesBtn = self.$('span.o_wslides_js_slide_like_up');
                const $likesIcon = $likesBtn.find('i.fa');
                const $dislikesBtn = self.$('span.o_wslides_js_slide_like_down');
                const $dislikesIcon = $dislikesBtn.find('i.fa');

                // update 'thumbs-up' button with latest state
                $likesBtn.data('user-vote', data.user_vote);
                $likesBtn.find('span').text(data.likes);
                $likesIcon.toggleClass("fa-thumbs-up", data.user_vote === 1);
                $likesIcon.toggleClass("fa-thumbs-o-up", data.user_vote !== 1);
                // update 'thumbs-down' button with latest state
                $dislikesBtn.data('user-vote', data.user_vote);
                $dislikesBtn.find('span').text(data.dislikes);
                $dislikesIcon.toggleClass("fa-thumbs-down", data.user_vote === -1);
                $dislikesIcon.toggleClass("fa-thumbs-o-down", data.user_vote !== -1);
            } else {
                if (data.error === 'public_user') {
                    const message = data.error_signup_allowed ?
                        _t('Please <a href="/web/login?redirect=%s">login</a> or <a href="/web/signup?redirect=%s">create an account</a> to vote for this lesson') :
                        _t('Please <a href="/web/login?redirect=%s">login</a> to vote for this lesson');
                    self._popoverAlert(self.$el, sprintf(message, encodeURIComponent(document.URL), encodeURIComponent(document.URL)));
                } else if (data.error === 'slide_access') {
                    self._popoverAlert(self.$el, _t('You don\'t have access to this lesson'));
                } else if (data.error === 'channel_membership_required') {
                    self._popoverAlert(self.$el, _t('You must be member of this course to vote'));
                } else if (data.error === 'channel_comment_disabled') {
                    self._popoverAlert(self.$el, _t('Votes and comments are disabled for this course'));
                } else if (data.error === 'channel_karma_required') {
                    self._popoverAlert(self.$el, _t('You don\'t have enough karma to vote'));
                } else {
                    self._popoverAlert(self.$el, _t('Unknown error'));
                }
            }
        });
    },

    _onClickUp: function (ev) {
        var slideId = $(ev.currentTarget).data('slide-id');
        return this._onClick(slideId, 'like');
    },

    _onClickDown: function (ev) {
        var slideId = $(ev.currentTarget).data('slide-id');
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
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        $('.o_wslides_js_slide_like').each(function () {
            defs.push(new SlideLikeWidget(self).attachTo($(this)));
        });
        return Promise.all(defs);
    },
});

export default {
    slideLikeWidget: SlideLikeWidget,
    websiteSlidesSlideLike: publicWidget.registry.websiteSlidesSlideLike
};
