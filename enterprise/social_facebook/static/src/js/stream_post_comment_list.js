/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentFacebook } from './stream_post_comment';

export class StreamPostCommentListFacebook extends StreamPostCommentList {
    /**
     * Update the likes count in the reactions.
     */
    _updateLikes(comment) {
        comment.reactions = comment.reactions || {};
        comment.reactions["LIKE"] = comment.user_likes
            ? Math.max(0, (comment.reactions["LIKE"] || 0) - 1)
            : (comment.reactions["LIKE"] || 0) + 1;
        comment.user_likes = !comment.user_likes;
    }

    toggleUserLikes(comment) {
        rpc('/social_facebook/like_comment', {
            stream_post_id: this.originalPost.id.raw_value,
            comment_id: comment.id,
            like: !comment.user_likes,
        });
        this._updateLikes(comment);
    }

    get commentComponent() {
        return StreamPostCommentFacebook;
    }

}
