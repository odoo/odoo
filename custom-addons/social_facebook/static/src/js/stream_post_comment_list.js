/** @odoo-module **/

import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentFacebook } from './stream_post_comment';

export class StreamPostCommentListFacebook extends StreamPostCommentList {

    toggleUserLikes(comment) {
        this.rpc('/social_facebook/like_comment', {
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
