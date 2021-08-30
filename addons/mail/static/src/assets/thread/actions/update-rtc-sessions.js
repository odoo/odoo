/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/updateRtcSessions
        [Action/params]
            record
                [type]
                    Thread
            rtcSessions
                [type]
                    Collection<Object>
                [description]
                    server representation of the current rtc sessions of the
                    channel
        [Action/behavior]
            :oldCount
                @record
                .{Thread/rtcSessions}
                .{Collection/length}
            {Record/update}
                [0]
                    @record
                [1]
                    [Thread/rtcSessions]
                        @rtcSessions
            {if}
                @record
                .{Thread/rtc}
            .{then}
                :newCount
                    @record
                    .{Thread/rtcSessions}
                    .{Collection/length}
                {if}
                    @newCount
                    .{>}
                        @oldCount
                .{then}
                    {SoundEffects/channelJoin}
                    .{SoundEffect/play}
                {if}
                    @newCount
                    .{<}
                        @oldCount
                .{then}
                    {SoundEffects/memberLeave}
                    .{SoundEffect/play}
            {if}
                @record
                .{Thread/rtc}
            .{then}
                {Rtc/filterCallees}
                    [0]
                        @record
                        .{Thread/rtc}
                    [1]
                        @record
                        .{Thread/rtcSessions}
`;
