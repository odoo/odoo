/** @odoo-module **/

import { StreamPostCommentList } from '@social/js/stream_post_comment_list';
import { StreamPostCommentLinkedin } from './stream_post_comment';

export class StreamPostCommentListLinkedin extends StreamPostCommentList {

    get commentComponent() {
        return StreamPostCommentLinkedin;
    }

}
