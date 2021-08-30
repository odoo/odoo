/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcCallViewerComponent
        [web.Element/style]
            [web.scss/position]
                relative
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/flex-direction]
                column
            [web.scss/height]
                50%
            [web.scss/min-height]
                50%
            {if}
                @record
                .{RtcCallViewerComponent/rtcCallViewer}
                .{RtcCallViewer/isMinimized}
            .{then}
                [web.scss/height]
                    20%
                [web.scss/min-height]
                    20%
            .{if}
                @record
                .{RtcCallViewerComponent/rtcCallViewer}
                .{RtcCallViewer/isFullScreen}
            .{then}
                [web.scss/position]
                    fixed
                [web.scss/z-index]
                    {scss/$zindex-fixed}
                [web.scss/top]
                    0
                [web.scss/left]
                    0
                [web.scss/width]
                    100vw
                [web.scss/height]
                    100vh
            [web.scss/background-color]
                {scss/lighten}
                    black
                    10%
`;
