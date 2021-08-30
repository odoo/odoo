/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last message considered by the server.

        Useful to compute localMessageUnreadCounter field.

        @see localMessageUnreadCounter
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            serverLastMessage
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Message
`;
