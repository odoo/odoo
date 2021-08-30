/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            participantContainer
        [Element/model]
            RtcCallViewerComponent
        [Element/onClick]
            {RtcCallViewer/onClick}
                [0]
                    @record
                    .{RtcCallViewerComponent/rtcCallViewer}
                [1]
                    @ev
        [Element/onMousemove]
            {RtcCallViewer/onMousemove}
                [0]
                    @record
                    .{RtcCallViewerComponent/rtcCallViewer}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/overflow]
                hidden
            [web.scss/height]
                100%
            [web.scss/width]
                100%
            [web.scss/display]
                flex;
            [web.scss/justify-content]
                space-between
`;
