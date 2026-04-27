/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { StreamPostComments } from '@social/js/stream_post_comments';
import { StreamPostCommentListInstagram } from './stream_post_comment_list';
import { StreamPostCommentsReplyInstagram } from './stream_post_comments_reply';
import { onWillStart } from "@odoo/owl";

export class StreamPostCommentsInstagram extends StreamPostComments {

    setup() {
        super.setup();

        this.commentsCount = this.props.commentsCount;
        this.totalLoadedComments = this.props.comments.length;
        this.state.showLoadMoreComments = !!this.props.nextRecordsToken;
        this.nextRecordsToken = this.props.nextRecordsToken;

        onWillStart(async () => {
            const instagramInfo = await this.orm.read(
                'social.account', [this.props.accountId], ['name', 'instagram_account_id']);

            this.mediaSpecificProps = Object.assign(this.mediaSpecificProps, {
                accountId: this.props.accountId,
                accountName: instagramInfo[0].name,
                instagramAccountId: instagramInfo[0].instagram_account_id,
            });
        });
    }

    async loadMoreComments() {
        const nextComments = await rpc('/social_instagram/get_comments', {
            stream_post_id: this.originalPost.id.raw_value,
            next_records_token: this.nextRecordsToken,
            comments_count: this.commentsCount
        });

        this.state.showLoadMoreComments = !!nextComments.nextRecordsToken;
        this.comments.push(...nextComments.comments);
        this.nextRecordsToken = nextComments.nextRecordsToken;
    }

    get commentListComponent() {
        return StreamPostCommentListInstagram;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyInstagram;
    }

}
