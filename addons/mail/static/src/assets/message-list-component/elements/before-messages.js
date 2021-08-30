/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            beforeMessages
        [Element/model]
            MessageListComponent
        [Element/isPresent]
            @record
            .{MessageListComponent/order}
            .{=}
                asc
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
                .{ThreadCache/orderedNonEmptyMessages}
                .{Collection/length}
                .{!=}
                    0
        [web.Element/class]
            flex-grow-1
`;
