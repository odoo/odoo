/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message is needaction. Useful to make it
        present in inbox mailbox and messaging menu.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isNeedaction
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
