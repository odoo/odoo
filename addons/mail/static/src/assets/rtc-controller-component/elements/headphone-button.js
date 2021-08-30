/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headphoneButton
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/button
        [Element/isPresent]
            @record
            .{RtcControllerComponent/rtcController}
            .{RtcController/callViewer}
            .{RtcCallViewer/threadView}
            .{TreadView/thread}
            .{Thread/rtc}
            .{&}
                {Rtc/currentRtcSession}
        [RtcControllerComponent/button/isActive]
            {Rtc/currentRtcSession}
            .{RtcSession/isDeaf}
            .{isFalsy}
        [web.Element/aria-label]
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isDeaf}
            .{then}
                {Locale/text}
                    Undeafen
            .{else}
                {Locale/text}
                    Deafen
        [web.Element/title]
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isDeaf}
            .{then}
                {Locale/text}
                    Undeafen
            .{else}
                {Locale/text}
                    Deafen
        [Element/onClick]
            {RtcController/onClickDeafen}
                [0]
                    {Rtc/currentRtcSession}
                [1]
                    @ev
`;
