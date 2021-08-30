/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            screenButton
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/videoButton
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
            {Rtc/sendDisplay}
        [web.Element/aria-label]
            {if}
                {Rtc/sendDisplay}
            .{then}
                {Locale/text}
                    Stop screen sharing
            .{else}
                {Locale/text}
                    Share screen
        [web.Element/title]
            {if}
                {Rtc/sendDisplay}
            .{then}
                {Locale/text}
                    Stop screen sharing
            .{else}
                {Locale/text}
                    Share screen
        [Element/onClick]
            {RtcController/onClickScreen}
                [0]
                    {Rtc/currentRtcSession}
                [1]
                    @ev
`;
