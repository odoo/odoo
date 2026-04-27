/** @odoo-module **/

import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentYoutube } from './stream_post_comment';

export class StreamPostCommentListYoutube extends StreamPostCommentList {

    get commentComponent() {
        return StreamPostCommentYoutube;
    }

}
