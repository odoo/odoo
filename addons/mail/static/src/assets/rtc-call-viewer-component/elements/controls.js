/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            controls
        [Element/model]
            RtcCallViewerComponent
        [Element/isPresent]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/showOverlay}
            .{|}
                @record
                .{RtcCallViewerComponent/rtcCallViewer}
                .{RtcCallViewer/isControllerFloating}
                .{isFalsy}
        [web.Element/style]
            [web.scss/width]
                100%
            [web.scss/display]
                flex
            [web.scss/justify-content]
                center
            [web.scss/padding-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    1
            {if}
                @record
                .{RtcCallViewerComponent/rtcCallViewer}
                .{RtcCallViewer/isControllerFloating}
            .{then}
                [web.scss/position]
                    absolute
                [web.scss/padding-bottom]
                    {scss/map-get}
                        {scss/$spacers}
                        3
                [web.scss/bottom]
                    0
`;
