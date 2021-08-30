/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The amount of videos broadcast in the current Rtc call
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            videoCount
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            0
        [Field/compute]
            @record
            .{Thread/rtcSessions}
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{RtcSession/videoStream}
            .{Collection/length}
`;
