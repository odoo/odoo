/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the message that's currently being replied to.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            replyingToMessageView
        [Field/model]
            ThreadView
        [Field/type]
            one
        [Field/target]
            MessageView
`;
