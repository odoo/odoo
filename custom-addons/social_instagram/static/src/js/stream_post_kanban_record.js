/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsInstagram } from './stream_post_comments';

import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

patch(StreamPostKanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        useEffect((commentEl) => {
            if (commentEl) {
                const onInstagramCommentsClick = this._onInstagramCommentsClick.bind(this);
                commentEl.addEventListener('click', onInstagramCommentsClick);
                return () => {
                    commentEl.removeEventListener('click', onInstagramCommentsClick);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_instagram_comments')]);
    },

    _onInstagramCommentsClick(ev) {
        ev.stopPropagation();
        const postId = this.record.id.raw_value;
        this.rpc('/social_instagram/get_comments', {
            stream_post_id: postId,
            comments_count: this.commentsCount,
        }).then((result) => {
            this.dialog.add(StreamPostCommentsInstagram, {
                title: _t('Instagram Comments'),
                commentCount: this.commentCount,
                originalPost: this.record,
                accountId: this.record.account_id.raw_value,
                postId: postId,
                comments: result.comments,
                nextRecordsToken: result.nextRecordsToken,
            });
        });
    },

});
