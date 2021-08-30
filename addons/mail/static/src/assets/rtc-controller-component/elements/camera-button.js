/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            cameraButton
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
            {Rtc/sendUserVideo}
        [web.Element/aria-label]
            {if}
                {Rtc/sendUserVideo}
            .{then}
                {Locale/text}
                    Stop camera
            .{else}
                {Locale/text}
                    Turn camera on
        [web.Element/title]
            {if}
                {Rtc/sendUserVideo}
            .{then}
                {Locale/text}
                    Stop camera
            .{else}
                {Locale/text}
                    Turn camera on
        [Element/onClick]
            {RtcController/onClickCamera}
                [0]
                    {Rtc/currentRtcSession}
                [1]
                    @ev
`;
