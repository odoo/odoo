/** @odoo-module **/

import { StreamPostCommentsReply } from '@social/js/stream_post_comments_reply';

export class StreamPostCommentsReplyInstagram extends StreamPostCommentsReply {

    get authorPictureSrc() {
        return '/social_instagram/static/src/img/instagram_user.png';
    }

    get canAddImage() {
        return false;
    }

    get addCommentEndpoint() {
        return '/social_instagram/comment';
    }

}
