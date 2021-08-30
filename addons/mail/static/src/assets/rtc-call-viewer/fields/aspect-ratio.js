/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The aspect ratio of the tiles.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            aspectRatio
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            Float
        [Field/default]
            16
            .{/}
                9
        [Field/compute]
            :rtcAspectRatio
                {Rtc/videoConfig}
                .{&}
                    {Rtc/videoConfig}
                    .{VideoConfig/aspectRatio}
            :aspectRatio
                @rtcAspectRatio
                .{|}
                    16
                    .{/}
                        9
            {Dev/comment}
                if we are in minimized mode (round avatar frames),
                we treat the cards like squares.
            {if}
                @record
                .{RtcCallViewer/isMinimized}
            .{then}
                1
            .{else}
                @aspectRatio
`;
