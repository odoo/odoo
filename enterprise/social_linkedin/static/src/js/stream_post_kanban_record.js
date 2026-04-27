/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsLinkedin } from './stream_post_comments';

import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

patch(StreamPostKanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        useEffect((commentEl) => {
            if (commentEl) {
                const onLinkedInCommentsClick = debounce(this._onLinkedInCommentsClick.bind(this), 300, true);
                commentEl.addEventListener('click', onLinkedInCommentsClick);
                return () => {
                    commentEl.removeEventListener('click', onLinkedInCommentsClick);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_linkedin_comments')]);
    },

    _onLinkedInCommentsClick(ev) {
        ev.stopPropagation();
        const postId = this.record.id.raw_value;
        rpc('/social_linkedin/get_comments', {
            stream_post_id: postId,
            comments_count: this.commentsCount
        }).then((result) => {
            const closeDialog = this.dialog.add(StreamPostCommentsLinkedin, {
                title: _t('LinkedIn Comments'),
                commentsCount: this.commentsCount,
                accountId: this.record.account_id.raw_value,
                originalPost: this.record,
                postId: postId,
                comments: result.comments,
                summary: result.summary,
                postAuthorImage: result.postAuthorImage,
                currentUserUrn: result.currentUserUrn,
                offset: result.offset,
                onPostUpdate: (newMessage) => this.props.record.update({message: newMessage}),
                onPostDeleted: async () => {
                    // remove the record from the kanban view
                    await this.props.record.model.root._removeRecords([this.props.record.id]);
                    closeDialog();
                },
            });
        });
    },
});
