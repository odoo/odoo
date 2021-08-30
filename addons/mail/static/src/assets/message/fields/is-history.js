/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message was a needaction. Useful to make it
        present in history mailbox.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isHistory
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
