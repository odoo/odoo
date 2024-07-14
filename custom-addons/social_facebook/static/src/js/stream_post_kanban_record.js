/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsFacebook } from './stream_post_comments';

import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

patch(StreamPostKanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        useEffect((commentEl) => {
            if (commentEl) {
                const onFacebookCommentsClick = this._onFacebookCommentsClick.bind(this);
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
        this.rpc('/social_facebook/get_comments', {
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
            });
        });
    },

    _onFacebookPostLike() {
        const userLikes = this.record.facebook_user_likes.raw_value;
        this.rpc('/social_facebook/like_post', {
            stream_post_id: this.record.id.raw_value,
            like: !userLikes
        });
        this._updateLikesCount('facebook_user_likes', 'facebook_likes_count');
    },

});
