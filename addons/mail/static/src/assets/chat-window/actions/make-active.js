/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Makes this chat window active, which consists of making it visible,
        unfolding it, and focusing it if the user isn't on a mobile device.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/makeActive
        [Action/params]
            chatWindow
                [type]
                    ChatWindow
            options
                [type]
                    Object
        [Action/behavior]
            {ChatWindow/makeVisible}
                @chatWindow
            {ChatWindow/unfold}
                @chatWindow
                @options
            :condition
                {if}
                    @options
                    .{&}
                        @options
                        .{Dict/hasKey}
                            focus
                .{then}
                    @options
                    .{Dict/get}
                        focus
                .{else}
                    {Device/isMobileDevice}
                    .{isFalsy}
            {if}
                @condition
            .{then}
                {ChatWindow/focus}
                    @chatWindow
`;
