import { htmlEscape, markup } from "@odoo/owl";

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

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
                return htmlEscape(message).toString();
            }
        });
        bsPopover.show();
        this.registerCleanup(() => bsPopover.dispose());
    }

    /**
     * @param {number} slideId
     * @param {string} voteType
     */
    async onClick(slideId, voteType) {
        const data = await this.waitFor(rpc('/slides/slide/like', {
            slide_id: slideId,
            upvote: voteType === 'like',
        }))
        if (!data.error) {
            const likeButtonEl = this.el.querySelector('span.o_wslides_js_slide_like_up');
            const likesIcon = likeButtonEl.querySelector('i.fa');
            const dislikeButtonEl = this.el.querySelector('span.o_wslides_js_slide_like_down');
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
                const tags = {
                    a_login_open: markup`<a href="/web/login?redirect=${encodeURIComponent(
                        document.URL
                    )}">`,
                    a_login_close: markup`</a>`,
                    a_signup_open: markup`<a href="/web/signup?redirect=${encodeURIComponent(
                        document.URL
                    )}">`,
                    a_signup_close: markup`</a>`,
                };
                this.showAlert(
                    data.error_signup_allowed
                        ? _t(
                              "Please %(a_login_open)slogin%(a_login_close)s or %(a_signup_open)screate an account%(a_signup_close)s to vote for this lesson",
                              tags
                          )
                        : _t(
                              "Please %(a_login_open)slogin%(a_login_close)s to vote for this lesson",
                              tags
                          )
                );
            } else if (data.error === 'slide_access') {
                this.showAlert(_t("You don't have access to this lesson"));
            } else if (data.error === "channel_membership_required") {
                this.showAlert(_t("You must be member of this course to vote"));
            } else if (data.error === "channel_comment_disabled") {
                this.showAlert(_t("Votes and comments are disabled for this course"));
            } else if (data.error === "channel_karma_required") {
                this.showAlert(_t("You don't have enough karma to vote"));
            } else {
                this.showAlert(_t("Unknown error"));
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.slide_like", SlideLike);
