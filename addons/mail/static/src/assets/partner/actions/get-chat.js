/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Gets the chat between the user of this partner and the current user.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/getChat
        [Action/params]
            partner
                [type]
                    Partner
        [Action/returns]
            Thread
        [Action/behavior]
            {if}
                @partner
                .{Partner/user}
                .{isFalsy}
                .{&}
                    @partner
                    .{Partner/hasCheckedUser}
                    .{isFalsy}
            .{then}
                {Record/doAsync}
                    [0]
                        @partner
                    [1]
                        {Partner/checkIsUser}
                            @partner
            {Dev/comment}
                prevent chatting with non-users
            {if}
                @partner
                .{Partner/user}
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
                            You can only chat with partners that have a dedicated user.
                    [type]
                        info
            .{else}
                {User/getChat}
                    @partner
                    .{Partner/user}
`;
