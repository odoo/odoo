/** @odoo-module **/

import { StreamPostCommentsReply } from '@social/js/stream_post_comments_reply';

import { sprintf } from '@web/core/utils/strings';

export class StreamPostCommentsReplyFacebook extends StreamPostCommentsReply {

    get authorPictureSrc() {
        return sprintf('https://graph.facebook.com/v17.0/%s/picture?height=48&width=48',
            this.props.mediaSpecificProps.pageFacebookId);
    }

    get addCommentEndpoint() {
        return '/social_facebook/comment';
    }

}
