/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            joinCallButton
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/callToggleButton
        [Element/isPresent]
            @record
            .{RtcControllerComponent/rtcController}
            .{RtcController/callViewer}
            .{RtcCallViewer/threadView}
            .{TreadView/thread}
            .{Thread/rtc}
            .{isFalsy}
        [web.Element/aria-label]
            {Locale/text}
                Join Video Call
        [web.Element/title]
            {Locale/text}
                Join Video Call
        [web.Element/isDisabled]
            @record
            .{RtcControllerComponent/rtcController}
            .{RtcController/callViewer}
            .{RtcCallViewer/threadView}
            .{TreadView/thread}
            .{Thread/hasPendingRtcRequest}
        [Element/onClick]
            {RtcController/onClickToggleVideoCall}
                [0]
                    {Rtc/currentRtcSession}
                [1]
                    @ev
`;
