/** @odoo-module **/

import { StreamPostComment } from '@social/js/stream_post_comment';
import { StreamPostCommentsReplyYoutube } from './stream_post_comments_reply';

export class StreamPostCommentYoutube extends StreamPostComment {

    //--------
    // Getters
    //--------

    get authorPictureSrc() {
        return this.comment.from.author_image_url;
    }

    /**
     * This is not *officially* supported by Google.
     * I retro-engineered the links they send by email to redirect the user to a specific comment
     * and this is a crafted URL that seems to work.
     * It sends the user to the video with the specific comment marked as "Highlighted Comment".
     *
     * Worst case scenario you just land on the video, which is fine too.
     */
    get link() {
        return `https://www.youtube.com/watch?v=${encodeURIComponent(this.originalPost.youtube_video_id.raw_value)}&lc=${encodeURIComponent(this.comment.id)}&feature=em-comments`
    }

    get authorLink() {
        return this.comment.from ? this.comment.from.author_channel_url : null;
    }

    get isAuthor() {
        return this.comment.from.id === this.props.mediaSpecificProps.youtubeChannelId;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReplyYoutube;
    }

    get deleteCommentEndpoint() {
        return '/social_youtube/delete_comment';
    }

    get isLikable() {
        return false;
    }

    get isDeletable() {
        return true;
    }

}
