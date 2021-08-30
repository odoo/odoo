/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            message
        [Element/model]
            MessageListComponent:messageContainer
        [Field/target]
            MessageViewComponent
        [Record/models]
            MessageListComponent/item
        [Element/isPresent]
            @record
            .{MessageListComponent:messageContainer/messageView}
            .{MessageView/message}
            .{Message/isEmpty}
            .{isFalsy}
        [MessageViewComponent/messageView]
            @record
            .{MessageListComponent:messageContainer/messageView}
        [web.Element/style]
            {if}
                @record
                .{MessageListComponent/selectedMessage}
                .{!=}
                    @record
                    .{MessageListComponent:messageContainer/message}
            .{then}
                {if}
                    @record
                    .{MessageListComponent/selectedMessage}
                .{then}
                    [web.scss/opacity]
                        0.5
`;
