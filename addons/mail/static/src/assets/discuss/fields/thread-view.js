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
            Discuss
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/related]
            Discuss/threadViewer
            ThreadViewer/threadView
`;
