/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guestAuthor
        [Field/model]
            Message
        [Field/type]
            one
        [Field/target]
            Guest
        [Field/inverse]
            Guest/authoredMessages
`;
