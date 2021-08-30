/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcController/onClickToggleAudioCall
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcController
        [Action/behavior]
            {if}
                @record
                .{RtcController/callViewer}
                .{RtcCallViewer/threadView}
                .{ThreadView/thread}
                .{Thread/hasPendingRtcRequest}
            .{then}
                {break}
            {Thread/toggleCall}
                @record
                .{RtcController/callViewer}
                .{CallViewer/threadView}
                .{ThreadView/thread}
`;
