/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message is starred. Useful to make it present
        in starred mailbox.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isStarred
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
