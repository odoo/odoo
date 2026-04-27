/** @odoo-module **/

import { StreamPostCommentsReply } from '@social/js/stream_post_comments_reply';

import { sprintf } from '@web/core/utils/strings';

export class StreamPostCommentsReplyTwitter extends StreamPostCommentsReply {

    get authorPictureSrc() {
        return sprintf('/web/image/social.account/%s/image/48x48', this.props.mediaSpecificProps.accountId);
    }

    get addCommentEndpoint() {
        return sprintf('/social_twitter/%s/comment', this.originalPost.stream_id.raw_value);
    }

}
