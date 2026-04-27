/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CANCEL_GLOBAL_CLICK, StreamPostKanbanRecord } from '@social/js/stream_post_kanban_record';
import { StreamPostCommentsYoutube } from './stream_post_comments';

import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";

patch(StreamPostKanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        useEffect((commentEl) => {
            if (commentEl) {
                const onYoutubeCommentsClick = debounce(this._onYoutubeCommentsClick.bind(this), 300, true);
                commentEl.addEventListener('click', onYoutubeCommentsClick);
                return () => {
                    commentEl.removeEventListener('click', onYoutubeCommentsClick);
                };
            }
        }, () => [this.rootRef.el.querySelector('.o_social_youtube_comments')]);
    },

    _onYoutubeCommentsClick(ev) {
        ev.stopPropagation();
        const postId = this.record.id.raw_value;
        rpc('/social_youtube/get_comments', {
            stream_post_id: postId,
            comments_count: this.commentsCount,
        }).then((result) => {
            this.dialog.add(StreamPostCommentsYoutube, {
                title: _t('YouTube Comments'),
                accountId: this.record.account_id.raw_value,
                originalPost: this.record,
                postId: postId,
                comments: result.comments,
                nextPageToken: result.nextPageToken,
            });
        });
    },

    onGlobalClick(ev) {
        if (ev.target.closest('.o_social_youtube_thumbnail')) {
            ev.preventDefault();
        } else if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        this.rootRef.el.querySelector('.o_social_comments').click();
    }

});
