/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens a chat between the user of this partner and the current user
        and returns it.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/openChat
        [Action/params]
            partner
                [type]
                    Partner
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
                        @partner
                    [1]
                        {Partner/getChat}
                            @partner
            {if}
                @chat
                .{isFalsy}
            .{then}
                {break}
            {Record/doAsync}
                [0]
                    @partner
                [1]
                    {Thread/open}
                        [0]
                            @chat
                        [1]
                            @options
            @chat
`;
