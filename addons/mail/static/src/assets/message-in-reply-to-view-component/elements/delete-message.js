/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            deleteMessage
        [Element/model]
            MessageInReplyToViewComponent
        [Element/isPresent]
            @record
            .{MessageInReplyToViewComponent/messageInReplyToView}
            .{MessageInReplyToView/messageView}
            .{MessageView/message}
            .{Message/parentMessage}
            .{Message/isEmpty}
        [web.Element/tag]
            i
        [web.Element/class]
            text-muted
            ml-2
        [web.Element/textContent]
            {Locale/text}
                Original message was deleted
`;
