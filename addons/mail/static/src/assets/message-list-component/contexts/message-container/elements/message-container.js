/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            Transition
        [Element/name]
            messageContainer
        [Element/model]
            MessageListComponent:messageContainer
        [Transition/visible]
            @record
            .{MessageListComponent:messageContainer/messageView}
            .{MessageView/message}
            .{=}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/thread}
                .{Thread/messageAfterNewMessageSeparator}
        [Transition/name]
            o-fade
        [Transition/t-slot-scope]
            transition
`;
