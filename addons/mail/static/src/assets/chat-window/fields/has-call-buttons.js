/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the buttons to start a RTC call should be displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasCallButtons
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{ChatWindow/thread}
            .{&}
                @record
                .{ChatWindow/thread}
                .{Thread/rtcSessions}
                .{Collection/length}
                .{=}
                    0
            .{&}
                {Record/insert}
                    [Record/models]
                        Collection
                    channel
                    chat
                    group
                .{Collection/includes}
                    @record
                    .{ChatWindow/thread}
                    .{Thread/channelType}
`;
