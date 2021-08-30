/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Message unread counter coming from server.

        Value of this field is unreliable, due to dynamic nature of
        messaging. So likely outdated/unsync with server. Should use
        localMessageUnreadCounter instead, which smartly guess the actual
        message unread counter at all time.

        @see localMessageUnreadCounter
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            serverMessageUnreadCounter
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;
