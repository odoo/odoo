/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsTwitter } from './stream_post_comments';
import { StreamPostTwitterQuote } from './stream_post_twitter_quote';

import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { sprintf } from '@web/core/utils/strings';
import { useService } from '@web/core/utils/hooks';
import { useEffect } from "@odoo/owl";

patch(StreamPostKanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        this.notification = useService('notification');

        useEffect((commentEl) => {
            if (commentEl) {
                const onTwitterCommentsClick = debounce(this._onTwitterCommentsClick.bind(this), 300, true);
                commentEl.addEventListener('click', onTwitterCommentsClick);
                return () => {
                    commentEl.removeEventListener('click', onTwitterCommentsClick);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_twitter_comments')]);
        useEffect((likeEl) => {
            if (likeEl) {
                const onTwitterTweetLike = this._onTwitterTweetLike.bind(this);
                likeEl.addEventListener('click', onTwitterTweetLike);
                return () => {
                    likeEl.removeEventListener('click', onTwitterTweetLike);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_twitter_likes')]);
        useEffect((retweetEl) => {
            if (retweetEl) {
                const onTwitterRetweet = this._onTwitterRetweet.bind(this);
                retweetEl.addEventListener('click', onTwitterRetweet);
                return () => {
                    retweetEl.removeEventListener('click', onTwitterRetweet);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_twitter_retweet')]);
        useEffect((quoteEl) => {
            if (quoteEl) {
                const onTwitterQuote = this._onTwitterQuote.bind(this);
                quoteEl.addEventListener('click', onTwitterQuote);
                return () => {
                    quoteEl.removeEventListener('click', onTwitterQuote);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_twitter_quote')]);
    },

    _onTwitterCommentsClick(ev) {
        ev.stopPropagation();
        const postId = this.record.id.raw_value;

        const modalInfo = {
            title: _t("Twitter Comments"),
            accountId: this.record.account_id.raw_value,
            originalPost: this.record,
            postId: postId,
            streamId: this.record.stream_id.raw_value,
        };

        rpc("/social_twitter/get_comments", { stream_post_id: postId })
            .then((result) => {
                this.dialog.add(StreamPostCommentsTwitter, {
                    ...modalInfo,
                    commentsCount: this.commentsCount,
                    allComments: result.comments,
                    comments: result.comments.slice(0, this.commentsCount),
                    isReplyLimited: result.is_reply_limited,
                });
            })
            .catch((error) => {
                this.dialog.add(StreamPostCommentsTwitter, {
                    ...modalInfo,
                    commentsCount: 0,
                    allComments: [],
                    comments: [],
                    isReplyLimited: true,
                    error: error.data.message,
                });
            });
    },

    async _onTwitterTweetLike() {
        const userLikes = this.record.twitter_user_likes.raw_value;
        rpc(sprintf('/social_twitter/%s/like_tweet', this.record.stream_id.raw_value), {
            tweet_id: this.record.twitter_tweet_id.raw_value,
            like: !userLikes
        });
        await this._updateLikesCount("twitter_user_likes", "twitter_likes_count");
    },

    _onTwitterRetweet(ev) {
        rpc(sprintf('/social_twitter/%s/%s', this.record.stream_id.raw_value,
                 this.record.twitter_can_retweet.raw_value ? 'retweet' : 'unretweet'), {
            tweet_id: this.record.twitter_tweet_id.raw_value,
            stream_id: this.record.stream_id.raw_value,
        }).then((result) => {
            result = JSON.parse(result);
            if (result === true) {
                const retweetCount = this.record.twitter_can_retweet.raw_value ?
                    this.record.twitter_retweet_count.raw_value + 1 :
                    this.record.twitter_retweet_count.raw_value - 1;
                this.props.record.update({
                    'twitter_can_retweet': !this.record.twitter_can_retweet.raw_value,
                    'twitter_retweet_count': retweetCount,
                });
            } else if (result.error) {
                this.notification.add(result.error, {
                    title: _t('Error'),
                    type: 'danger',
                });
            }
        });
    },

    _onTwitterQuote() {
        this.dialog.add(StreamPostTwitterQuote, {
            title: _t('Quote a Tweet'),
            mediaSpecificProps: {
                accountId: this.record.account_id.raw_value,
                accountName: this.record.author_name.value,
            },
            originalPost: this.record,
            refreshStats: () => this.env.refreshStats(),
        });
    },

});
