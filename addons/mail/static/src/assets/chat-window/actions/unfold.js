/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/unfold
        [Action/params]
            chatWindow
            [notifyServer]
                [target]
                    Boolean
                [default]
                    {Device/isMobile}
                    .{isFalsy}
        [Action/behavior]
            {Record/update}
                [0]
                    @chatWindow
                [1]
                    [ChatWindow/isFolded]
                        false
            {Dev/comment}
                Flux specific: manually opening the chat window should save
                the new state on the server.
            {if}
                @chatWindow
                .{ChatWindow/thread}
                .{&}
                    @notifyServer
                .{&}
                    {Env/currentGuest}
            .{then}
                {Thread/notifyFoldStateToServer}
                    [0]
                        @chatWindow
                        .{ChatWindow/thread}
                    [1]
                        open
`;
