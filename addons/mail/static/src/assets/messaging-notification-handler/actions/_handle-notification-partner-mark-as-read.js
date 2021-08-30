/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationPartnerMarkAsRead
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            message_ids
                [type]
                    Collection<Integer>
            needaction_inbox_counter
                [type]
                    Integer
        [Action/behavior]
            {Dev/comment}
                1. move messages from inbox to history
            {foreach}
                @message_ids
            .{as}
                message_id
            .{do}
                {Dev/comment}
                    We need to ignore all not yet known messages because
                    we don't want them to be shown partially as they
                    would be linked directly to cache. Furthermore,
                    server should not send back all message_ids marked as
                    read but something like last read message_id or
                    something like that. (just imagine you mark 1000
                    messages as read ... )
                :message
                    {Record/findById}
                        [Message/id]
                            @message_id
                {if}
                    @message
                    .{isFalsy}
                .{then}
                    {continue}
                {Dev/comment}
                    update thread counter
                {if}
                    @message
                    .{Message/originThread}
                    .{&}
                        @message
                        .{Message/isNeedaction}
                .{then}
                    {Record/update}
                        [0]
                            @message
                            .{Message/originThread}
                        [1]
                            [Thread/messageNeedactionCounter]
                                {Field/remove}
                                    1
                {Dev/comment}
                    move messages from Inbox to history
                {Record/update}
                    [0]
                        @message
                    [1]
                        [Message/isHistory]
                            true
                        [Message/isNeedaction]
                            false
            {if}
                @needaction_inbox_counter
                .{!=}
                    undefined
            .{then}
                {Record/update}
                    [0]
                        {Env/inbox}
                    [1]
                        [Thread/counter]
                            @needaction_inbox_counter
            .{else}
                {Dev/comment}
                    kept for compatibility in stable
                {Record/update}
                    [0]
                        {Env/inbox}
                    [1]
                        [Thread/counter]
                            {Field/remove}
                                @message_ids
                                .{Collection/length}
            {if}
                {Env/inbox}
                .{Thread/counter}
                .{>}
                    {Env/inbox}
                    .{Thread/cache}
                    .{ThreadCache/fetchedMessages}
                    .{Collection/length}
            .{then}
                {Dev/comment}
                    Force refresh Inbox because depending on what was
                    marked as read the cache might become empty even
                    though there are more messages on the server.
                {Record/update}
                    [0]
                        {Env/inbox}
                        .{Thread/cache}
                    [1]
                        [ThreadCache/hasToLoadMessages]
                            true
`;
