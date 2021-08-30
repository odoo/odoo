/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens a chat between this user and the current user and returns it.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            User/openChat
        [Action/params]
            user
                [type]
                    User
            options
                [type]
                    Object
                [description]
                    forwarded to @see Thread/open
        [Action/returns]
            Thread
        [Action/behavior]
            :chat
                {Record/doAsync}
                    [0]
                        @user
                    [1]
                        {User/getChat}
                            @user
            {if}
                @chat
                .{isFalsy}
            .{then}
                {break}
            {Record/doAsync}
                [0]
                    @user
                [1]
                    {Thread/open}
                        [0]
                            @chat
                        [1]
                            @options
            @chat
`;
