/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the message view that controls this message action list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageView
        [Field/model]
            MessageActionList
        [Field/type]
            one
        [Field/target]
            MessageView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            MessageView/messageActionList
`;
