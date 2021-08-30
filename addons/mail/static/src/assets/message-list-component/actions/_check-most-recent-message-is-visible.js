/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_checkMostRecentMessageIsVisible
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/behavior]
            {if}
                {MessageListComponent/getMostRecentMessageViewComponent}
                    @record
                .{&}
                    {MessageViewComponent/isPartiallyVisible}
                        {MessageListComponent/getMostRecentMessageViewComponent}
                            @record
            .{then}
                :lastMessageView
                    @record
                    .{MessageListComponent/messageListView}
                    .{MessageListView/threadViewOwner}
                    .{ThreadView/lastMessageView}
                {if}
                    @lastMessageView
                    .{&}
                        @lastMessageView
                        .{MessageView/component}
                    .{&}
                        {MessageViewComponent/isPartiallyVisible}
                            @lastMessageView
                            .{MessageView/component}
                .{then}
                    {ThreadView/handleVisibleMessage}
                        [0]
                            @record
                            .{MessageListComponent/messageListView}
                            .{MessageListView/threadViewOwner}
                        [1]
                            @lastMessageView
                            .{MessageView/message}
`;
