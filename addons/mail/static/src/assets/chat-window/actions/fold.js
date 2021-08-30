/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/fold
        [Action/params]
            chatWindow
            notifyServer
                [type]
                    boolean
                [default]
                    {Device/isMobile}
        [Action/behavior]
            {Record/update}
                [0]
                    @chatWindow
                [1]
                    [ChatWindow/isFolded]
                        true
            {Dev/comment}
                Flux specific: manually folding the chat window should save
                the new state on the server.
            {if}
                @chatWindow
                .{ChatWindow/thread}
                .{&}
                    @notifyServer
                .{&}
                    {Env/currentGuest}
                    .{isFalsy}
            .{then}
                {Thread/notifyFoldStateToServer}
                    [0]
                        @chatWindow
                        .{ChatWindow/thread}
                    [1]
                        folded
`;
