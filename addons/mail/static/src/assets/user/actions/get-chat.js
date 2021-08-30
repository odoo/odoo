/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Gets the chat between this user and the current user.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            User/getChat
        [Action/params]
            user
                [type]
                    User
        [Action/returns]
            Thread
        [Action/behavior]
            {if}
                @user
                .{User/partner}
                .{isFalsy}
            .{then}
                {Record/doAsync}
                    [0]
                        @user
                    [1]
                        {User/fetchPartner}
                            @user
            {if}
                @user
                .{User/partner}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    This user has been deleted from the server or never existed:
                    - Validity of id is not verified at insert.
                    - There is no bus notification in case of user delete from
                      another tab or by another user.
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    notification
                .{Dict/get}
                    notify
                .{Function/call}
                    [message]
                        {Locale/text}
                            You can only chat with existing users.
                    [type]
                        warning
                {break}
            {Dev/comment}
                in other cases a chat would be valid, find it or try to create it
            :chat
                {Record/find}
                    [Record/models]
                        Thread
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{Thread/channelType}
                            .{=}
                                chat
                            .{&}
                                @item
                                .{Thread/correspondent}
                                .{=}
                                    @user
                                    .{User/partner}
                            .{&}
                                @item
                                .{Thread/model}
                                .{=}
                                    mail.channel
                            .{&}
                                @item
                                .{Thread/public}
                                .{=}
                                    private
            {if}
                @chat
                .{isFalsy}
                .{|}
                    @chat
                    .{Thread/isPinned}
                    .{isFalsy}
            .{then}
                {Dev/comment}
                    if chat is not pinned then it has to be pinned client-side
                    and server-side, which is a side effect of following rpc
                :chat
                    {Record/doAsync}
                        [0]
                            @user
                        [1]
                            {Thread/performRpcCreateChat}
                                [partnerIds]
                                    @user
                                    .{User/partner}
                                    .{Partner/id}
            {if}
                @chat
                .{isFalsy}
            .{then}
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    notification
                .{Dict/get}
                    notify
                .{Function/call}
                    [message]
                        {Locale/text}
                            An unexpected error occurred during the creation of the chat.
                    [type]
                        warning
                {break}
            @chat
`;
