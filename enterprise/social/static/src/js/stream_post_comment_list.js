/** @odoo-module **/

import { StreamPostComment } from './stream_post_comment';
import { Component } from "@odoo/owl";

export class StreamPostCommentList extends Component {
    static template = "social.StreamPostCommentsWrapper";
    static props = {
        comments: Array,
        account: {type: Object, optional: true},
        error: {type: String, optional: true},
        mediaSpecificProps: Object,
        originalPost: Object,
        preventAddComment: Function,
    };

    /**
     * To override for each specific social StreamPostCommentList class.
     * 
     * @param comment
     */
    toggleUserLikes(comment) {}


    _updateLikes(comment) {
        if (comment.user_likes) {
            if (comment.likes.summary.total_count > 0)
                comment.likes.summary.total_count--;
        } else {
            comment.likes.summary.total_count++;
        }
        comment.user_likes = !comment.user_likes;
    }

    get comments() {
        return this.props.comments;
    }

    get account() {
        return this.props.account;
    }

    get originalPost() {
        return this.props.originalPost;
    }

    get commentComponent() {
        return StreamPostComment;
    }

}
