/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separatorDate
        [Element/model]
            MessageListComponent:messageContainer
        [Record/models]
            MessageListComponent/item
            MessageListComponent/separator
        [Element/isPresent]
            @record
            .{MessageListComponent:messageContainer/messageView}
            .{MessageView/message}
            .{Message/isEmpty}
            .{isFalsy}
            .{&}
                @template
                .{Template/currentDay}
                .{!=}
                    @template
                    .{Template/messageDay}
        [web.Element/class]
            pt-4
`;
