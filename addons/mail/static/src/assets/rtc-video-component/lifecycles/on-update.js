/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Since it is not possible to directly put a mediaStreamObject as the src
        or src-object of the template, the video src is manually inserted into
        the DOM.
    {Lifecycle}
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            RtcVideoComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{RtcVideoComponent/rtcSession}
                .{RtcSession/videoStream}
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @root
                    [1]
                        [web.Element/srcObject]
                            {Record/empty}
            .{else}
                {Record/update}
                    [0]
                        @root
                    [1]
                        [web.Element/srcObject]
                            @record
                            .{RtcVideoComponent/rtcSession}
                            .{RtcSession/videoStream}
            {web.Element/load}
                @root
`;
