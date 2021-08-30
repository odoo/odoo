/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussPublicView
        [Field/model]
            ThreadViewer
        [Field/type]
            one
        [Field/target]
            DiscussPublicView
        [Field/inverse]
            DiscussPublicView/threadViewer
        [Field/isReadonly]
            true
`;
