/** @odoo-module **/

import { StreamPostComments } from '@social/js/stream_post_comments';
import { StreamPostCommentListLinkedin } from './stream_post_comment_list';
import { StreamPostCommentsReplyLinkedin } from './stream_post_comments_reply';

export class StreamPostCommentsLinkedin extends StreamPostComments {

    setup() {
        super.setup();

        this.commentsCount = this.props.commentsCount;
        this.totalLoadedComments = this.props.comments.length;
        this.state.showLoadMoreComments = this.totalLoadedComments < this.props.summary.total_count;
        this.offset = this.props.offset;

        this.mediaSpecificProps = Object.assign(this.mediaSpecificProps, {
            accountId: this.props.accountId,
            accountName: '',
            postAuthorImage: this.props.postAuthorImage,
            currentUserUrn: this.props.currentUserUrn,
        });
    }

    async loadMoreComments() {
        const nextComments = await this.rpc('/social_linkedin/get_comments', {
            stream_post_id: this.originalPost.id.raw_value,
            offset: this.offset,
            comments_count: this.commentsCount
        });

        this.totalLoadedComments += nextComments.comments.length;
        if (this.totalLoadedComments >= this.props.summary.total_count) {
            this.state.showLoadMoreComments = false;
        }
        this.comments.push(...nextComments.comments);
        this.offset = nextComments.offset;
    }

    get commentListComponent() {
        return StreamPostCommentListLinkedin;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyLinkedin;
    }

}
