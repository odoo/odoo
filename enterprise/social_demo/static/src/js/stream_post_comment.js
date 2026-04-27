/** @odoo-module **/

import { StreamPostCommentFacebook } from '@social_facebook/js/stream_post_comment';
import { StreamPostCommentInstagram } from '@social_instagram/js/stream_post_comment';
import { StreamPostCommentLinkedin } from '@social_linkedin/js/stream_post_comment';
import { StreamPostCommentTwitter } from '@social_twitter/js/stream_post_comment';
import { StreamPostCommentYoutube } from '@social_youtube/js/stream_post_comment';

import { patch } from "@web/core/utils/patch";

const getDemoAuthorPictureSrc = function() {
    return this.comment.from.profile_image_url_https;
};

patch(StreamPostCommentFacebook.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentInstagram.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentLinkedin.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentTwitter.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});

patch(StreamPostCommentYoutube.prototype, {

    get authorPictureSrc() {
        return getDemoAuthorPictureSrc.apply(this, arguments);
    }

});
