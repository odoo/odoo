/** @odoo-module **/

import { StreamPostComment } from '@social/js/stream_post_comment';
import { StreamPostCommentsReplyLinkedin } from './stream_post_comments_reply';

import { rpc } from "@web/core/network/rpc";
import { sprintf } from '@web/core/utils/strings';

export class StreamPostCommentLinkedin extends StreamPostComment {

    async _onReplyComment() {
        if (!this.action.showReplyComment) {
            await this._onLoadReplies();
        }
        await super._onReplyComment();
    }

    async _onLoadReplies() {
        const innerComments = await rpc('/social_linkedin/get_comments', {
            stream_post_id: this.originalPost.id.raw_value,
            comment_urn: this.comment.id,
            comments_count: this.commentsCount
        });
        this.comment.comments.data = innerComments.comments;

        super._onLoadReplies();
    }

    //--------
    // Getters
    //--------

    get authorPictureSrc() {
        return this.comment.from.picture;
    }

    get link() {
        let activityUrn = this.comment.id.split('(')[1].split(',')[0];
        return sprintf('https://www.linkedin.com/feed/update/%s?commentUrn=%s', encodeURIComponent(activityUrn), encodeURIComponent(this.comment.id));
    }

    get authorLink() {
        if (this.comment.from.isOrganization) {
            return `https://www.linkedin.com/company/${encodeURIComponent(this.comment.from.vanityName)}`;
        }
        return `https://www.linkedin.com/in/${encodeURIComponent(this.comment.from.vanityName)}`;
    }

    get isAuthor() {
        return this.comment.from.id === this.props.mediaSpecificProps.currentUserUrn;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyLinkedin;
    }

    get deleteCommentEndpoint() {
        return '/social_linkedin/delete_comment';
    }

    get isLikable() {
        return true;
    }

    get isEditable() {
        return true;
    }

    /**
     * Linkedin stores the created time in milliseconds (number)
     *
     * @returns {DateTime}
     */
    get commentCreatedTime() {
        const createdTime = super.commentCreatedTime;
        return !createdTime.invalid ? createdTime : luxon.DateTime.fromMillis(this.comment.created_time);
    }
}
