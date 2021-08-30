/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messages
        [Field/model]
            ThreadView
        [Field/type]
            many
        [Field/target]
            Message
        [Field/related]
            ThreadView/threadCache
            ThreadCache/messages
`;
