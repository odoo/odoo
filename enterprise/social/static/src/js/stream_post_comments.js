/** @odoo-module **/

import { ImagesCarouselDialog } from "./images_carousel_dialog";
import { StreamPostCommentList } from "./stream_post_comment_list";
import { StreamPostCommentsReply } from "./stream_post_comments_reply";
import { SocialPostFormatterMixin } from "./social_post_formatter_mixin";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Component, markup, useSubEnv, useState } from "@odoo/owl";

export class StreamPostComments extends SocialPostFormatterMixin(Component) {
    static template = "social.StreamPostComments";
    static components = { Dialog };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.dialog = useService('dialog');
        this.comments = useState(this.props.comments);
        this.postId = this.props.postId;

        this.state = useState({
            displayModal: true,
            showLoadMoreComments: false,
            isEditMode: false,
            // because this component is inside a modal, it's not possible to
            // change his props from his parent with a event handler without
            // re-creating the modal, so we duplicate the message into the state
            message: this._formatStreamPostForEdition(this.originalPost.message.raw_value),
        });

        this.mediaSpecificProps = {};

        useSubEnv({
            closeCommentsModal: this.closeCommentsModal.bind(this)
        });
    }

    //----------
    // Handlers
    //----------

    onClickMoreImages(index, images) {
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

    onDeletePost() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Post"),
            body: _t("Do you really want to delete this Post ?"),
            confirm: async () => {
                await rpc(`/social_${this.props.originalPost.media_type.raw_value}/delete_post`, {
                    stream_post_id: this.originalPost.id.raw_value,
                });
                if (this.props.onPostDeleted) {
                    this.props.onPostDeleted();
                }
            },
            confirmLabel: _t("Delete"),
            cancel: () => {},
        });
    }

    async onEditPost(event) {
        const textarea = event.currentTarget;
        if (
            event.key !== "Enter" ||
            event.ctrlKey ||
            event.shiftKey ||
            textarea.value.trim() === ""
        ) {
            return;
        }

        this.state.isEditMode = false;
        this.state.message = textarea.value;

        await rpc(`/social_${this.props.originalPost.media_type.raw_value}/edit_post`, {
            stream_post_id: this.originalPost.id.raw_value,
            new_message: textarea.value,
        });

        this.props?.onPostUpdate(textarea.value);
    }

    preventAddComment(textarea, replyToCommentId) {
        return false;
    }

    _formatCommentStreamPost(message) {
        return markup(this._formatPost(message));
    }

    _formatStreamPostForEdition(message) {
        return message;
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

    get isDeletable() {
        return false;
    }

    get isEditable() {
        return false;
    }
}
