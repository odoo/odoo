/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        currentDay: 0
        prevMessage: 0

        for message of getOrderedMessages():
            if message === threadView.thread(mself).messageAfterNewMessageSeparator(mself):
                <separatorNewMessages/>
            if message not empty:
                messageDay: getDateDay(message)
                if currentDay !== messageDay:
                    <separatorDate/>
                    currentDay: messageDay
                    isMessageSquashed: false
                if currentDay === messageDay:
                    isMessageSquashed: shouldMessageBeSquashed(prevMessage, message)
                <message/>
                prevMessage: message
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            messageContainerForeach
        [Element/model]
            MessageListComponent
        [Record/models]
            Foreach
        [Field/target]
            MessageListComponent:messageContainer
        [MessageListComponent:messageContainer/messageView]
            @field
            .{Foreach/get}
                messageView
        [Foreach/collection]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{ThreadView/messageViews}
        [Foreach/as]
            messageView
        [Element/key]
            @field
            .{Foreach/get}
                messageView
            .{Record/id}
`;
