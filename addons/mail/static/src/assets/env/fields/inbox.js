/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mailbox Inbox.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            inbox
        [Field/model]
            Env
        [Field/type]
            one
        [Field/target]
            Thread
`;
