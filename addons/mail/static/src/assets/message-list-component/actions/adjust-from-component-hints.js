/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Update the scroll position of the message list.
        This is not done in patched/mounted hooks because scroll position is
        dependent on UI globally. To illustrate, imagine following UI:

        +----------+ < viewport top = scrollable top
        | message  |
        |   list   |
        |          |
        +----------+ < scrolltop = viewport bottom = scrollable bottom

        Now if a composer is mounted just below the message list, it is shrinked
        and scrolltop is altered as a result:

        +----------+ < viewport top = scrollable top
        | message  |
        |   list   | < scrolltop = viewport bottom  <-+
        |          |                                  |-- dist = composer height
        +----------+ < scrollable bottom            <-+
        +----------+
        | composer |
        +----------+

        Because of this, the scroll position must be changed when whole UI
        is rendered. To make this simpler, this is done when <ThreadView/>
        component is patched. This is acceptable when <ThreadView/> has a
        fixed height, which is the case for the moment. task-2358066
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/adjustFromComponentHints
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/behavior]
            :componentHintList
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/componentHintList}
            {foreach}
                @componentHintList
            .{as}
                hint
            .{do}
                {switch}
                    @hint
                    .{Hint/type}
                .{case}
                    {Dev/comment}
                        thread just became visible, the goal is to restore its
                        saved position if it exists or scroll to the end
                    [change-of-thread-cache]
                        {MessageListComponent/_adjustScrollFromModel}
                            @record
                    [member-list-hidden]
                        {MessageListComponent/_adjustScrollFromModel}
                            @record
                    {Dev/comment}
                        messages have been added at the end, either scroll to the
                        end or keep the current position
                    [message-received]
                        {MessageListComponent/_adjustScrollForExtraMessagesAtTheEnd}
                            @record
                    [messages-loaded]
                        {MessageListComponent/_adjustScrollForExtraMessagesAtTheEnd}
                            @record
                    [new-messages-loaded]
                        {MessageListComponent/_adjustScrollForExtraMessagesAtTheEnd}
                            @record
                    [more-messages-loaded]
                        {MessageListComponent/_adjustFromMoreMessagesLoaded}
                            [0]
                                @record
                            [1]
                                @hint
                {ThreadView/markComponentHintProcessed}
                    [0]
                        @record
                        .{MessageListComponent/messageListView}
                        .{MessageListView/threadViewOwner}
                    [1]
                        @hint
            {Record/update}
                [0]
                    @record
                [1]
                    [MessageListComponent/_willPatchSnapshot]
                        {Record/empty}
`;
