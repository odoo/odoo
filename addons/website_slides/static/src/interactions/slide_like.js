import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { sprintf } from '@web/core/utils/strings';
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class SlideLike extends Interaction {
    static selector = ".o_wslides_js_slide_like";
    dynamicContent = {
        ".o_wslides_js_slide_like_up": { "t-on-click": (ev) => this.onClick(ev.currentTarget.dataset.slideId, 'like') },
        ".o_wslides_js_slide_like_down": { "t-on-click": (ev) => this.onClick(ev.currentTarget.dataset.slideId, 'dislike') },
    };

    /**
     * @param {String} message
     */
    showAlert(message) {
        const bsPopover = window.Popover.getOrCreateInstance(this.el, {
            trigger: 'focus',
            delay: { 'hide': 300 },
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        });
        bsPopover.show();
        this.registerCleanup(() => bsPopover.dispose());
    }

    async onClick(slideId, voteType) {
        const data = await this.waitFor(rpc('/slides/slide/like', {
            slide_id: slideId,
            upvote: voteType === 'like',
        }))
        if (!data.error) {
            const likeButtonEl = document.querySelector('span.o_wslides_js_slide_like_up');
            const likesIcon = likeButtonEl.querySelector('i.fa');
            const dislikeButtonEl = document.querySelector('span.o_wslides_js_slide_like_down');
            const dislikesIcon = dislikeButtonEl.querySelector('i.fa');

            // update 'thumbs-up' button with latest state
            likeButtonEl.dataset.userVote = data.user_vote;
            likeButtonEl.querySelector('span').innerText = data.likes;
            likesIcon.classList.toggle("fa-thumbs-up", data.user_vote === 1);
            likesIcon.classList.toggle("fa-thumbs-o-up", data.user_vote !== 1);
            // update 'thumbs-down' button with latest state
            dislikeButtonEl.dataset.userVote = data.user_vote;
            dislikeButtonEl.querySelector('span').innerText = data.dislikes;
            dislikesIcon.classList.toggle("fa-thumbs-down", data.user_vote === -1);
            dislikesIcon.classList.toggle("fa-thumbs-o-down", data.user_vote !== -1);
        } else {
            if (data.error === 'public_user') {
                const message = data.error_signup_allowed ?
                    _t('Please <a href="/web/login?redirect=%(url)s">login</a> or <a href="/web/signup?redirect=%(url)s">create an account</a> to vote for this lesson') :
                    _t('Please <a href="/web/login?redirect=%(url)s">login</a> to vote for this lesson');
                this.showAlert(sprintf(message, { url: encodeURIComponent(document.URL) }));
            } else if (data.error === 'slide_access') {
                this.showAlert(_t('You don\'t have access to this lesson'));
            } else if (data.error === 'channel_membership_required') {
                this.showAlert(_t('You must be member of this course to vote'));
            } else if (data.error === 'channel_comment_disabled') {
                this.showAlert(_t('Votes and comments are disabled for this course'));
            } else if (data.error === 'channel_karma_required') {
                this.showAlert(_t('You don\'t have enough karma to vote'));
            } else {
                this.showAlert(_t('Unknown error'));
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.slide_like", SlideLike);
