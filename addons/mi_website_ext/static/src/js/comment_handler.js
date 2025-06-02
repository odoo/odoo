/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.CommentSystem = publicWidget.Widget.extend({
    selector: '.comment_section',
    events: {
        'click .send_button': '_onSendComment',
        'click .reply-button': '_onReply',
        'click .cancel-reply': '_onCancelReply',
        'click .like-comment-button': '_onLikeComment',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.replyingToCommentId = null;
    },

    _onSendComment: function (ev) {
        const $button = $(ev.currentTarget);
        const $input = this.$('.insert_comment');
        const content = $input.val();
        const publicationId = this.$el.data('publication-id');
        const resModel = this.$el.data('res-model'); // <-- Nuevo
        const resId = this.$el.data('res-id');   

        if (!content.trim() || !resModel || !resId) {
            return;
        }

        $button.prop('disabled', true);

        rpc.query({
            route: '/portal/add_comment', // <-- Nueva ruta
            params: {
                res_model: resModel,      // <-- Nuevo
                res_id: resId,            // <-- Nuevo
                content: content,
                parent_id: this.replyingToCommentId,
            },
        }).then((result) => {
            if (result.error) {
                alert(result.error);
            } else {
                // Idealmente aquí se usaría una plantilla QWeb del lado del cliente para renderizar el nuevo comentario.
                // Por simplicidad, recargaremos la página para ver el nuevo comentario.
                // Esto es menos dinámico pero funciona como primer paso.
                window.location.reload();  
            }
        }).catch(() => {
            alert('Ocurrió un error. Intenta de nuevo.');
        }).finally(() => {
            $button.prop('disabled', false);
            $input.val('');
            this._onCancelReply();
        });
    },

    _onReply: function (ev) {
        const $button = $(ev.currentTarget);
        this.replyingToCommentId = $button.data('comment-id');
        const authorName = $button.data('author-name');

        this.$('.replying-to-section').show();
        this.$('.reply-to-name').text(authorName);
        this.$('.insert_comment').attr('placeholder', `Respondiendo a ${authorName}...`).focus();
    },

    _onCancelReply: function () {
        this.replyingToCommentId = null;
        this.$('.replying-to-section').hide();
        this.$('.insert_comment').attr('placeholder', 'Escribe un comentario...');
    },

    _onLikeComment: function (ev) {
        const $button = $(ev.currentTarget);
        const commentId = $button.data('comment-id');

        rpc.query({
            route: '/comment/toggle_like',
            params: { comment_id: commentId },
        }).then((result) => {
            if (result.success) {
                // Actualizar el UI del like dinámicamente
                const $icon = $button.find('i');
                const $countSpan = $button.siblings('.like-count');

                $countSpan.text(result.like_count);
                if (result.liked) {
                    $icon.removeClass('fa-heart-o text-muted').addClass('fa-heart text-danger');
                } else {
                    $icon.removeClass('fa-heart text-danger').addClass('fa-heart-o text-muted');
                }
            }
        });
    },
});