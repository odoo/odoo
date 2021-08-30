/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread view linked to this discuss public view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadView
        [Field/model]
            DiscussPublicView
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/isReadonly]
            true
        [Field/related]
            DiscussPublicView/threadViewer
            ThreadViewer/threadView
`;
