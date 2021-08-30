/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Starts editing the last message of this thread from the current user.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadView/startEditingLastMessageFromCurrentUser
        [Action/params]
            record
                [type]
                    ThreadView
        [Action/behavior]
            :messageViews
                @record.
                {ThreadView/messageViews}
            {Collection/reverse}
                @messageViews
            :messageView
                @messageViews
                .{Collection/find}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            messageView
                        [Function/out]
                            @messageView
                            .{MessageView/message}
                            .{Message/isCurrentUserOrGuestAuthor}
                            .{&}
                                @messageView
                                .{MessageView/message}
                                .{Message/canBeDeleted)
            {if}
                @messageView
            .{then}
                {MessageView/startEditing}
                    @messageView
`;
