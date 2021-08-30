/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            messageInReplyToView
        [Element/model]
            MessageViewComponent
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/messageInReplyToView}
        [Field/target]
            MessageInReplyToViewComponent
        [MessageInReplyToViewComponent/messageInReplyToView]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/messageInReplyToView}
`;
