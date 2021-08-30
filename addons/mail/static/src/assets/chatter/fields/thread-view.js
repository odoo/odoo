/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the 'ThreadView' displaying 'this.thread'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadView
        [Field/model]
            Chatter
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/related]
            Chatter/threadViewer
            ThreadViewer/threadView
`;
