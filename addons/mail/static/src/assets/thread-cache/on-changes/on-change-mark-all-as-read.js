/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Not a real field, used to trigger its compute method when one of the
        dependencies changes.
    {onChange}
        [onChange/name]
            onChangeMarkAllAsRead
        [onChange/model]
            ThreadCache
        [onChange/dependencies]
            ThreadCache/isLoaded
            ThreadCache/isLoading
            ThreadCache/isMarkAllAsReadRequested
            ThreadCache/thread
                Thread/isTemporary
            ThreadCache/thread
                Thread/model
            ThreadCache/threadViews
        {Dev/comment}
            Calls "mark all as read" when this thread becomes displayed in a
            view (which is notified by isMarkAllAsReadRequested being true),
            but delays the call until some other conditions are met, such as the
            messages being loaded.
            The reason to wait until messages are loaded is to avoid a race
            condition because "mark all as read" will change the state of the
            messages in parallel to fetch reading them.
        [onChange/behavior]
            {if}
                {Env/currentGuest}
            .{then}
                {break}
            {if}
                @record
                .{ThreadCache/isMarkAllAsReadRequested}
                .{isFalsy}
                .{|}
                    @record
                    .{ThreadCache/thread}
                    .{isFalsy}
                .{|}
                    @record
                    .{ThreadCache/isLoaded}
                    .{isFalsy}
                .{|}
                    @record
                    .{ThreadCache/isLoading}
            .{then}
                {Dev/comment}
                    wait for change of state before
                    deciding what to do
                {break}
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadCache/isMarkAllAsReadRequested]
                        false
            {if}
                @record
                .{ThreadCache/thread}
                .{Thread/isTemporary}
                .{|}
                    @record
                    .{ThreadCache/thread}
                    .{Thread/model}
                    .{=}
                        mail.box
                .{|}
                    @record
                    .{ThreadCache/threadViews}
                    .{Collection/length}
                    .{=}
                        0
            .{then}
                {Dev/comment}
                    ignore the request
                {break}
            {Message/markAllAsRead}
                model
                .{=}
                    @record
                    .{ThreadCache/thread}
                    .{Thread/model}
                .{&}
                    res_id
                    .{=}
                        @record
                        .{ThreadCache/thread}
                        .{Thread/id}
`;
