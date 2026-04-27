/** @odoo-module **/

import { StreamPostCommentsReply } from '@social/js/stream_post_comments_reply';

export class StreamPostCommentsReplyLinkedin extends StreamPostCommentsReply {

    get authorPictureSrc() {
        return this.props.mediaSpecificProps.postAuthorImage;
    }

    get canAddImage() {
        return true;
    }

    get addCommentEndpoint() {
        return '/social_linkedin/comment';
    }

    get allowImageOnlyComment() {
        return true;
    }
}
