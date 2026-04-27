/** @odoo-module **/

import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentTwitter } from './stream_post_comment';

import { rpc } from "@web/core/network/rpc";
import { sprintf } from '@web/core/utils/strings';

export class StreamPostCommentListTwitter extends StreamPostCommentList {

    toggleUserLikes(comment) {
        rpc(sprintf('/social_twitter/%s/like_tweet', this.originalPost.stream_id.raw_value), {
            tweet_id: comment.id,
            like: !comment.user_likes,
        });
        this._updateLikes(comment);
    }

    get commentComponent() {
        return StreamPostCommentTwitter;
    }

}
