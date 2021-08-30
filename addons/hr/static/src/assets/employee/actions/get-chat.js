/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Gets the chat between the user of this employee and the current user.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Employee/getChat
        [Action/params]
            employee
        [Action/behavior]
            {if}
                @employee
                .{Employee/user}
                .{isFalsy}
                .{&}
                    @employee
                    .{Employee/hasCheckedUser}
                    .{isFalsy}
            .{then}
                {Record/doAsync}
                    []
                        @employee
                    []
                        {Employee/checkIsUser}
                            @employee
            {Dev/comment}
                prevent chatting with non-users
            {if}
                @employee
                .{Employee/user}
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
                            You can only chat with employees that have a dedicated user.
                    [type]
                        info
            .{else}
                {User/getChat}
                    @employee
                    .{Employee/user}
`;
