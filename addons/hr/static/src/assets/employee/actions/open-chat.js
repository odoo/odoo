/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens a chat between the user of this employee and the current user
        and returns it.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Employee/openChat
        [Action/params]
            employee
                [type]
                    Employee
            options
                [description]
                    forwarded to Thread/open
        [Action/behavior]
            :chat
                {Record/doAsync}
                    []
                        @employee
                    []
                        {Employee/getChat}
                            @employee
            {if}
                @chat
                .{isFalsy}
            .{then}
                {break}
            {Record/doAsync}
                []
                    @employee
                []
                    {Thread/open}
                        @chat
                        @options
            @chat
`;
