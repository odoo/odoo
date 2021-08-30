/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last message in the context of the currently displayed thread cache.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastMessage
        [Field/model]
            ThreadView
        [Field/type]
            one
        [Field/target]
            Message
        [Field/related]
            ThreadView/thread
            Thread/lastMessage
`;
