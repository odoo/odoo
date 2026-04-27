/** @odoo-module **/

import { StreamPostComments } from '@social/js/stream_post_comments';
import { StreamPostCommentListLinkedin } from './stream_post_comment_list';
import { StreamPostCommentsReplyLinkedin } from './stream_post_comments_reply';
import { LINKEDIN_HASHTAG_REGEX } from "./social_post_formatter_mixin";

import { onWillStart, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";


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

        this.aclState = useState({
            isDeletable: false,
            isEditable: false,
        });

        onWillStart(async () => {
            [this.aclState.isDeletable, this.aclState.isEditable] = await Promise.all([
                user.checkAccessRight("social.stream.post", "unlink"),
                user.checkAccessRight("social.stream.post", "write"),
            ]);
        });
    }

    async loadMoreComments() {
        const nextComments = await rpc('/social_linkedin/get_comments', {
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

    _formatStreamPostForEdition(message) {
        return message.replace(LINKEDIN_HASHTAG_REGEX, "#$1");
    }

    get commentListComponent() {
        return StreamPostCommentListLinkedin;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyLinkedin;
    }

    get isDeletable() {
        return this.aclState.isDeletable;
    }

    get isEditable() {
        return this.aclState.isEditable;
    }
}
