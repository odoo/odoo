/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the message that is displayed by this message view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            message
        [Field/model]
            MessageView
        [Field/type]
            one
        [Field/target]
            Message
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            Message/messageViews
`;
