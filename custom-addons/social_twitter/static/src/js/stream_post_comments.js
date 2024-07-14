/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { StreamPostComments } from '@social/js/stream_post_comments';
import { StreamPostCommentListTwitter } from './stream_post_comment_list';
import { StreamPostCommentsReplyTwitter } from './stream_post_comments_reply';
import { onWillStart } from "@odoo/owl";

const MAX_ALLOWED_REPLIES = 3;

export class StreamPostCommentsTwitter extends StreamPostComments {

    setup() {
        super.setup();

        this.page = 1;
        this.commentsCount = this.props.commentsCount;
        this.allComments = this.props.allComments;
        this.state.showLoadMoreComments = this.allComments.length > this.commentsCount;

        onWillStart(async () => {
            const twitterUserInfo = await this.orm.read(
                'social.account', [this.props.accountId], ['name', 'twitter_user_id', 'social_account_handle']);

            this.mediaSpecificProps = Object.assign(this.mediaSpecificProps, {
                accountId: this.props.accountId,
                accountName: twitterUserInfo[0].name,
                twitterUserId: twitterUserInfo[0].twitter_user_id,
                twitterUserScreenName: twitterUserInfo[0].social_account_handle,
            });
        });
    }

    /**
     * Twitter is a bit special as it does not handle the "load more", we receive all comments
     * at once. To avoid flooding the UI, we manually split the array to simulate a load more
     * behavior.
     */
    async loadMoreComments() {
        this.page += 1;
        var start = (this.page - 1) * this.commentsCount;
        var end = start + this.commentsCount;

        this.comments.push(...this.allComments.slice(start, end));

        if (end >= this.allComments.length) {
            this.state.showLoadMoreComments = false;
        }
    }

    onAddComment(comment) {
        super.onAddComment(...arguments);
        this.allComments.push(comment);
    }

    preventAddComment(textarea, replyToCommentId) {
        if (!this.props.isReplyLimited) {
            return false;
        }

        const allCommentsFlatten = this.allComments.reduce((result, currentComment) => {
            if (currentComment.comments) {
                const subComments = currentComment.comments.data;
                result.push(currentComment, ...subComments);
            } else {
                result.push(currentComment);
            }
            return result;
        }, []);

        const tweetId = String(
            replyToCommentId ? replyToCommentId : this.originalPost.twitter_tweet_id.raw_value
        );
        const existingAnswers = allCommentsFlatten.filter(
            (comment) =>
                comment.from &&
                comment.from.screen_name === this.mediaSpecificProps.twitterUserScreenName &&
                String(comment.in_reply_to_tweet_id) === tweetId
        );

        if (existingAnswers.length >= MAX_ALLOWED_REPLIES) {
            textarea.disabled = true;
            const textAreaMessage = textarea
                .closest('.o_social_write_reply')
                .querySelector('.o_social_textarea_message');
            textAreaMessage.classList.add('text-danger');
            textAreaMessage.textContent = _t(
                "Easy, tiger! No spamming allowed. Let's stick to three replies per Tweet."
            );
            return true;
        }

        return false;
    }

    get commentListComponent() {
        return StreamPostCommentListTwitter;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyTwitter;
    }

}
