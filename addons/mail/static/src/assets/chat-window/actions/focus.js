/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Programmatically auto-focus an existing chat window.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/focus
        [Action/params]
            record
                [type]
                    ChatWindow
        [Action/behavior]
            {if}
                @record
                .{ChatWindow/thread}
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ChatWindow/isDoFocus]
                            true
            {if}
                @record
                .{ChatWindow/threadVie}
                .{&}
                    @record
                    .{ChatWindow/threadView}
                    .{ThreadView/composerView}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{ChatWindow/threadView}
                        .{ThreadView/composerView}
                    [1]
                        [ComposerView/doFocus]
                            true
`;
