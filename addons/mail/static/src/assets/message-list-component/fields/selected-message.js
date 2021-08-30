/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            selectedMessage
        [Field/model]
            MessageListComponent
        [Field/type]
            one
        [Field/target]
            Message
`;
