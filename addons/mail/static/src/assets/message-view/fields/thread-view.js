/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread view that is displaying this messages (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadView
        [Field/model]
            MessageView
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/isReadonly]
            true
        [Field/inverse]
            ThreadView/messageViews
`;
