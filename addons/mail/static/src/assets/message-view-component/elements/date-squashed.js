/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dateSquashed
        [Element/model]
            MessageViewComponent
        [Record/models]
            MessageViewComponent/date
            MessageViewComponent/sidebarItem
        [web.Element/class]
            mt-1
        [Element/isPresent]
            @record
            .{MessageViewComponent/isActive}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/isSquashed}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/date}
        [web.Element/textContent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/date}
            .Moment/format
                hh:mm
`;
