/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            callVideoButton
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/model}
                .{=}
                    mail.channel
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/rtcSessions}
                .{Collection/length}
                .{=}
                    0
        [Record/models]
            ThreadViewTopbarComponent/button
        [web.Element/isActive]
            true
        [web.Element/isDisabled]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{Thread/hasPendingRtcRequest}
        [web.Element/title]
            {Locale/text}
               Start a Video Call
        [Element/onClick]
            {if}
                @record
                .{ThreadViewTopbarComponent/threadViewTopBar}
                .{ThreadViewTopbar/thread}
                .{Thread/hasPendingRtcRequest}
            .{then}
                {break}
            {Thread/toggleCall}
                [0]
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                    .{ThreadViewTopbar/thread}
                [1]
                    [startWithVideo]
                        true
`;
