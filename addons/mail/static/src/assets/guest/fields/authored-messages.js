/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            authoredMessages
        [Field/model]
            Guest
        [Field/type]
            many
        [Field/target]
            Message
        [Field/inverse]
            Message/guestAuthor
`;
