/** @odoo-module **/

import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentLinkedin } from './stream_post_comment';
import { rpc } from "@web/core/network/rpc";

export class StreamPostCommentListLinkedin extends StreamPostCommentList {
    async toggleUserLikes(comment) {
        await rpc("/social_linkedin/like_comment", {
            stream_post_id: this.originalPost.id.raw_value,
            comment_id: comment.id,
            like: !comment.user_likes,
        });
        this._updateLikes(comment);
    }

    get commentComponent() {
        return StreamPostCommentLinkedin;
    }

}
