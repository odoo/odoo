/** @odoo-module **/

import { StreamPostCommentsReplyFacebook } from '@social_facebook/js/stream_post_comments_reply';
import { StreamPostCommentsReplyInstagram } from '@social_instagram/js/stream_post_comments_reply';
import { StreamPostCommentsReplyLinkedin } from '@social_linkedin/js/stream_post_comments_reply';
import { StreamPostCommentsReplyTwitter } from '@social_twitter/js/stream_post_comments_reply';
import { StreamPostCommentsReplyYoutube } from '@social_youtube/js/stream_post_comments_reply';

import { patch } from "@web/core/utils/patch";

const getDemoAuthorPictureSrc = function() {
    return '/web/image/res.partner/2/image_128';
};

patch(StreamPostCommentsReplyFacebook.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentsReplyInstagram.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentsReplyLinkedin.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentsReplyTwitter.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentsReplyYoutube.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});
