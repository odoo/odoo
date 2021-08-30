/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        cleanly removes the video stream of the session
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcSession/removeVideo
        [Action/params]
            record
                [type]
                    RtcSession
        [Action/behavior]
            {if}
                @record
                .{RtcSession/videoStream}
            .{then}
                {foreach}
                    {VideoStream/getTracks}
                        @record
                        .{RtcSession/videoStream}
                .{as}
                    track
                .{do}
                    {Track/stop}
                        @track
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcSession/videoStream]
                        {Record/empty}
`;
