/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Call all sessions for which no peerConnection is established at
        a regular interval to try to recover any connection that failed
        to start.

        This is distinct from this._recoverConnection which tries to restores
        connection that were established but failed or timed out.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            autorecoveringInterval
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            {Browser/setInterval}
                [0]
                    {if}
                        @record
                        .{Rtc/currentRtcSession}
                        .{isFalsy}
                        .{|}
                            @record
                            .{Rtc/channel}
                            .{isFalsy}
                    .{then}
                        {break}
                    {Rtc/_pingServer}
                        @record
                    {if}
                        @record
                        .{Rtc/currentRtcSession}
                        .{isFalsy}
                        .{|}
                            @record
                            .{Rtc/channel}
                            .{isFalsy}
                    .{then}
                        {break}
                    {Rtc/_callSession}
                        @record
                [1]
                    30000
`;
