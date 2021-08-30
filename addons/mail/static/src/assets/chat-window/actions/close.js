/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Close this chat window.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/close
        [Action/params]
            chatWindow
            [notifyServer]
                [type]
                    boolean
                [default]
                    {Device/isMobile}
                    .{isFalsy}
        [Action/behavior]
            {if}
                {Device/isMobile}
                .{&}
                    {Discuss/discussView}
                    .{isFalsy}
            .{then}
                {Dev/comment}
                    If we are in mobile and discuss is not open, it
                    means the chat window was opened from the messaging
                    menu. In that case it should be re-opened to simulate
                    it was always there in the background.
                {Record/update}
                    [0]
                        {Env/messagingMenu}
                    [1]
                        [MessagingMenu/isOpen]
                            true
            {Dev/comment}
                Flux specific: 'closed' fold state should only be saved
                on the server when manually closing the chat window.
                Delete at destroy or sync from server value for example
                should not save the value.
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
                        closed
            {if}
                .{Record/exists}
                    @chatWindow
            .{then}
                {Record/delete}
                    @chatWindow
`;
