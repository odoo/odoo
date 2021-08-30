/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcController/onClickToggleVideoCall
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
                [0]
                    @record
                    .{RtcController/callViewer}
                    .{CallViewer/threadView}
                    .{ThreadView/thread}
                [startWithVideo]
                    true
`;
