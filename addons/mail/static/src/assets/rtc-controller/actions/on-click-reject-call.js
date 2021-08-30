/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcController/onClickRejectCall
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
            {Thread/leaveCall}
                @record
                .{RtcController/callViewer}
                .{RtcCallViewer/threadView}
                .{threadView/thread}
`;
