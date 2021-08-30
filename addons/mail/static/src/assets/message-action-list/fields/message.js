/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the message on which this action message list operates.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            message
        [Field/model]
            MessageActionList
        [Field/type]
            one
        [Field/target]
            Message
        [Field/related]
            MessageActionList/messageView
            MessageView/message
`;
