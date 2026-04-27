/** @odoo-module **/

import { StreamPostComments } from '@social/js/stream_post_comments';
import { StreamPostCommentListYoutube } from './stream_post_comment_list';
import { StreamPostCommentsReplyYoutube } from './stream_post_comments_reply';

import { rpc } from "@web/core/network/rpc";

import { onWillStart } from "@odoo/owl";

export class StreamPostCommentsYoutube extends StreamPostComments {

    setup() {
        super.setup();

        this.nextPageToken = this.props.nextPageToken;
        this.commentsCount = this.props.commentsCount;
        this.state.showLoadMoreComments = !!this.nextPageToken;

        onWillStart(async () => {
            const youtubeInfo = await this.orm.read(
                'social.account', [this.props.accountId], ['name', 'youtube_channel_id']);

            this.mediaSpecificProps = Object.assign(this.mediaSpecificProps, {
                accountId: this.props.accountId,
                accountName: youtubeInfo[0].name,
                youtubeChannelId: youtubeInfo[0].youtube_channel_id,
            });
        });
    }

    async loadMoreComments() {
        const nextComments = await rpc('/social_youtube/get_comments', {
            stream_post_id: this.originalPost.id.raw_value,
            next_page_token: this.nextPageToken,
            comments_count: this.commentsCount
        });

        this.comments.push(...nextComments.comments);
        this.nextPageToken = nextComments.nextPageToken;
        this.state.showLoadMoreComments = !!this.nextPageToken;
    }

    get commentListComponent() {
        return StreamPostCommentListYoutube;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyYoutube;
    }

}
