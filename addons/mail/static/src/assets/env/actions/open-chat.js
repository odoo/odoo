/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens a chat with the provided person and returns it.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/openChat
        [Action/params]
            options
                [description]
                    forwared to Thread/open
            person
                [description]
                    person forwarded to Env/getChat
        [Action/behavior]
            :chat
                {Record/doAsync}
                    [0]
                        @env
                    [1]
                        {Env/getChat}
                            @person
            {if}
                @chat
                .{isFalsy}
            .{then}
                {break}
            {Record/doAsync}
                [0]
                    @env
                [1]
                    {Thread/open}
                        [0]
                            @chat
                        [1]
                            options
            @chat
`;
