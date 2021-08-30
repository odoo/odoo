/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Used to trigger 'Thread/markAsSeen' when one of
        the dependencies changes.
    {onChange}
        [onChange/name]
            onThreadShouldBeSetAsSeen
        [onChange/model]
            ThreadView
        [onChange/dependencies]
            ThreadView/isComposerFocused
            ThreadView/lastMessage
            ThreadView/thread
                Thread/lastNonTransientMessage
            ThreadView/lastVisibleMessage
            ThreadView/threadCache
        [onChange/behavior]
            {if}
                @record
                .{ThreadView/thread}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{ThreadView/thread}
                .{Thread/lastNonTransientMessage}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{ThreadView/lastVisibleMessage}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{ThreadView/lastVisibleMessage}
                .{!=}
                    @record
                    .{ThreadView/lastMessage}
            .{then}
                {break}
            {if}
                @record
                .{ThreadView/isComposerFocused}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    FIXME condition should not be on "composer is focused" but
                    "threadView is active"
                    See task-2277543
                {break}
            {if}
                {Env/currentGuest}
            .{then}
                {break}
            {Thread/markAsSeen}
                [0]
                    @record
                    .{ThreadView/thread}
                [1]
                    @record
                    .{ThreadView/thread}
                    .{Thread/lastNonTransientMessage}
            .{Promise/catch}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        error
                    [Function/out]
                        {Dev/comment}
                            prevent crash when executing compute during destroy
                        {if}
                            @error
                            .{!=}
                                RecordDeletedError
                        .{then}
                            {Error/throw}
                                @error
`;
