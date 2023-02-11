/** @odoo-module **/

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
                self.$el.find('span.o_wslides_js_slide_like_up span').text(data.likes);
                self.$el.find('span.o_wslides_js_slide_like_down span').text(data.dislikes);
            } else {
                if (data.error === 'public_user') {
                    var message = _t('Please <a href="/web/login?redirect=%s">login</a> to vote this lesson');
                    var signupAllowed = data.error_signup_allowed || false;
                    if (signupAllowed) {
                        message = _t('Please <a href="/web/signup?redirect=%s">create an account</a> to vote this lesson');
                    }
                    self._popoverAlert(self.$el, _.str.sprintf(message, (document.URL)));
                } else if (data.error === 'vote_done') {
                    self._popoverAlert(self.$el, _t('You have already voted for this lesson'));
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
