/** @odoo-module **/

import { KanbanRecord } from '@web/views/kanban/kanban_record';
import { useService } from '@web/core/utils/hooks';

export const CANCEL_GLOBAL_CLICK = ["a", ".o_social_subtle_btn", "img"].join(",");
const DEFAULT_COMMENT_COUNT = 20;

export class StreamPostKanbanRecord extends KanbanRecord {

    setup() {
        super.setup();
        this.rpc = useService('rpc');
    }

    //---------------------------------------
    // Handlers
    //---------------------------------------

    /**
     * @override
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        this.rootRef.el.querySelector('.o_social_comments').click();
    }

    //---------------------------------------
    // Private
    //---------------------------------------

    _updateLikesCount(userLikeField, likesCountField) {
        const userLikes = this.props.record.data[userLikeField];
        let likesCount = this.props.record.data[likesCountField];
        if (userLikes) {
            if (likesCount > 0) {
                likesCount--;
            }
        } else {
            likesCount++;
        }

        this.props.record.update({
            [userLikeField]: !userLikes,
            [likesCountField]: likesCount,
        });
    }

    //---------
    // Getters
    //---------

    get commentCount() {
        return this.props.commentCount || DEFAULT_COMMENT_COUNT;
    }
}
