/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ImagesCarouselDialog } from './images_carousel_dialog';
import { SocialPostFormatterMixin } from './social_post_formatter_mixin';
import { StreamPostCommentsReply } from './stream_post_comments_reply';
import { StreamPostCommentList } from './stream_post_comment_list';

import { Dialog } from '@web/core/dialog/dialog';
import { useService } from '@web/core/utils/hooks';
import { Component, markup, useSubEnv, useState } from "@odoo/owl";

export class StreamPostComments extends SocialPostFormatterMixin(Component) {

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        this.dialog = useService('dialog');
        this.comments = useState(this.props.comments);
        this.postId = this.props.postId;

        this.state = useState({
            displayModal: true,
            showLoadMoreComments: false,
        });

        this.mediaSpecificProps = {};

        useSubEnv({
            closeCommentsModal: this.closeCommentsModal.bind(this)
        });
    }

    //----------
    // Handlers
    //----------

    _onClickMoreImages(index, images) {
        this.dialog.add(ImagesCarouselDialog, {
            title: _t("Post Images"),
            activeIndex: index,
            images: images
        })
    }

    closeCommentsModal() {
        this.state.displayModal = false;
    }

    loadMoreComments() {
        // to be defined by social-media sub-implementations
    }

    onAddComment(newComment) {
        this.comments.unshift(newComment);
    }

    preventAddComment(textarea, replyToCommentId) {
        return false;
    }

    _formatCommentStreamPost(message) {
        return markup(this._formatPost(message));
    }

    get bodyClass() {
        return 'o_social_comments_modal o_social_comments_modal_' + this.originalPost.media_type.raw_value + ' pt-0 px-0 bg-100';
    }

    get originalPost() {
        return this.props.originalPost;
    }

    get JSON() {
        return JSON;
    }

    get commentListComponent() {
        return StreamPostCommentList;
    }

    get commentReplyComponent() {
        return StreamPostCommentsReply;
    }

    get isAuthor() {
        return this.originalPost.is_author && this.originalPost.is_author.raw_value;
    }
}

StreamPostComments.template = 'social.StreamPostComments';
StreamPostComments.components = { Dialog };
