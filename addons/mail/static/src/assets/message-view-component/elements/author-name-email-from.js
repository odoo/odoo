/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            authorNameEmailFrom
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            a
        [Record/models]
            MessageViewComponent/authorName
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/author}
            .{isFalsy}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/emailFrom}
        [web.Element/href]
            mailto:
            .{+}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/emailFrom}
            .{+}
                ?subject=Re:
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/subject}
            .{then}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/subject}
        [web.Element/textContent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/emailFrom}
`;
