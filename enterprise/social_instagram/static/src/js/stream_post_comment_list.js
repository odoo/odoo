/** @odoo-module **/

import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentInstagram } from './stream_post_comment';

export class StreamPostCommentListInstagram extends StreamPostCommentList {

    get commentComponent() {
        return StreamPostCommentInstagram;
    }

}
