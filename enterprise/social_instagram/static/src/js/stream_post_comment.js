/** @odoo-module **/

import { StreamPostComment } from '@social/js/stream_post_comment';
import { StreamPostCommentsReplyInstagram } from './stream_post_comments_reply';

import { sprintf } from '@web/core/utils/strings';

export class StreamPostCommentInstagram extends StreamPostComment {

    //--------
    // Getters
    //--------

    get authorPictureSrc() {
        return sprintf('https://graph.facebook.com/v17.0/%s/picture',
            this.originalPost.instagram_facebook_author_id.raw_value);
    }

    get link() {
        return sprintf('https://www.instagram.com/%s', encodeURI(this.comment.from.name));
    }

    get authorLink() {
        return this.originalPost.post_link.raw_value;
    }

    get isAuthor() {
        return this.comment.from.id === this.props.mediaSpecificProps.instagramAccountId;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyInstagram;
    }

    get deleteCommentEndpoint() {
        return '/social_instagram/delete_comment';
    }

    get likesClass() {
        return 'fa-heart';
    }

    get isLikable() {
        return false;
    }

    get isDeletable() {
        return true;
    }

    get isEditable() {
        return false;
    }

}
