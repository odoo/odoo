/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageView
        [Field/model]
            MessageInReplyToView
        [Field/type]
            one
        [Field/target]
            MessageView
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageView/messageInReplyToView
`;
