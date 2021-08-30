/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            author
        [Element/model]
            MessageInReplyToViewComponent
        [Element/isPresent]
            @record
            .{MessageInReplyToViewComponent/messageInReplyToView}
            .{MessageInReplyToView/messageView}
            .{MessageView/message}
            .{Message/parentMessage}
            .{Message/isEmpty}
            .{isFalsy}
        [web.Element/tag]
            b
        [web.Element/class]
            text-muted
            ml-2
        [web.Element/textContent]
            {String/atSign}
            .{+}
                @record
                .{MessageInReplyToViewComponent/messageInReplyToView}
                .{MessageInReplyToView/messageView}
                .{MessageView/message}
                .{Message/parentMessage}
                .{Message/authorName}
`;
