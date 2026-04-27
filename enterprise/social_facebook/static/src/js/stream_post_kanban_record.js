/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsFacebook } from './stream_post_comments';

import { debounce } from "@web/core/utils/timing";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

patch(StreamPostKanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        useEffect((commentEl) => {
            if (commentEl) {
                const onFacebookCommentsClick = debounce(this._onFacebookCommentsClick.bind(this), 300, true);
                commentEl.addEventListener('click', onFacebookCommentsClick);
                return () => {
                    commentEl.removeEventListener('click', onFacebookCommentsClick);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_facebook_comments')]);
        useEffect((likeEl) => {
            if (likeEl) {
                const onFacebookPostLike = this._onFacebookPostLike.bind(this);
                likeEl.addEventListener('click', onFacebookPostLike);
                return () => {
                    likeEl.removeEventListener('click', onFacebookPostLike);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_facebook_likes')]);
    },

    _onFacebookCommentsClick(ev) {
        ev.stopPropagation();
        const postId = this.record.id.raw_value;
        rpc('/social_facebook/get_comments', {
            stream_post_id: postId,
            comments_count: this.commentsCount,
        }).then((result) => {
            this.dialog.add(StreamPostCommentsFacebook, {
                title: _t('Facebook Comments'),
                accountId: this.record.account_id.raw_value,
                originalPost: this.record,
                commentsCount: this.commentsCount,
                postId: postId,
                comments: result.comments,
                summary: result.summary,
                nextRecordsToken: result.nextRecordsToken,
                onFacebookPostLike: this._onFacebookPostLike.bind(this),
            });
        });
    },

    async _onFacebookPostLike() {
        const userLikes = this.record.facebook_user_likes.raw_value;
        rpc("/social_facebook/like_post", {
            stream_post_id: this.record.id.raw_value,
            like: !userLikes,
        });
        await this._updateLikesCount("facebook_user_likes", "facebook_likes_count");
    },

    /**
     * Prepare `additionnalValues` to update the reactions count.
     */
    _prepareLikeAdditionnalValues(likesCount, userLikes) {
        const additionnalValues = super._prepareLikeAdditionnalValues(likesCount, userLikes);

        if (this.record.media_type.raw_value === "facebook") {
            const reactionsCount = JSON.parse(this.record.facebook_reactions_count.raw_value);
            reactionsCount["LIKE"] = userLikes
                ? (reactionsCount["LIKE"] || 0) + 1
                : Math.max(0, (reactionsCount["LIKE"] || 0) - 1);
            additionnalValues.facebook_reactions_count = JSON.stringify(reactionsCount);
        }
        return additionnalValues;
    },
});
